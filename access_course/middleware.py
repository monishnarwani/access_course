"""
This file implements the Middleware support for the Open edX platform.
A access course enables the following features:

1) Setting refresh token in wordpress session
2) logout the user if wordpress session logged out

"""
from .utils import verify_usertoken, refresh_usertoken, check_subscription
from django.contrib.auth import logout
from django.conf import settings
from django.shortcuts import redirect
import json, time
from django.utils.http import cookie_date
from student.cookies import get_user_info_cookie_data
from opaque_keys.edx.keys import CourseKey, UsageKey
from openedx.core.lib.url_utils import unquote_slashes
from opaque_keys import InvalidKeyError
from django.http import HttpResponse
from django.contrib.auth.models import AnonymousUser
import logging
log = logging.getLogger(__name__)

class AccessCourseMiddleware(object):
    """
    Middleware class which will -  
    i)  set refresh token in wordpress session to keep session alive.
    ii) logout user from openedx if wordpress session is logged out.
    """

    def __init__(self):
        self.session_cookie_name = settings.BOP_CONFIGURATION.get('WRDPRS_COOKIE_NAME', '')
        self.bypass_req_urls = settings.BOP_CONFIGURATION.get('BYPASS_URLS', [])
        self.logout_url = "/logout"
        self.user_logged_out = False
        self.process_req_resp = False
        if settings.BOP_CONFIGURATION.get('ENABLE_ACCESS_COURSE_MIDDLEWARE', False) and self.session_cookie_name != '':
            self.process_req_resp = True
        self.cookie_settings = {
           'max_age': None, 
           'expires': None, 
           'domain': settings.SESSION_COOKIE_DOMAIN, 
           'path': '/', 
           'httponly': None
        }

    def get_updated_cookie_settings(self, request):
        if request.session.get_expire_at_browser_close():
            max_age = None
            expires = None
        else:
            max_age = request.session.get_expiry_age()
            expires_time = time.time() + max_age
            expires = cookie_date(expires_time)
        cookie_settings = {
           'max_age': max_age, 
           'expires': expires, 
           'domain': settings.SESSION_COOKIE_DOMAIN, 
           'path': '/', 
           'httponly': None
        }
        return cookie_settings

    def process_request(self, request):

        # if valid request and valid configuration then only process
        if self.process_req_resp and request.path not in self.bypass_req_urls:
            # if WP cookie is not set then logout
            # if WP cookie is set with empty value then logout
            # if WP cookie is set with some value then check if token is active, if not then logout
            # if token is active then cross check WP user info with openedx logged in user info based on email id, if details do not match then logout
            log.info('---------------------REQUEST-----------------------------')
            log.info(request.path)
            logout_user = False
            token = ''

            if request.COOKIES.has_key(self.session_cookie_name):
                token = request.COOKIES[self.session_cookie_name]

            # token = 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoiNGFkMjlhZWItMTczMC00NTU3LWFlNDEtMDQzZjY5M2M0ZTZmIiwidXNlcm5hbWUiOiJzaGV3ZXRhLnRoYXJhbmlAZm9jYWx3b3Jrcy5pbiIsImV4cCI6MTU1NzMxNTI0OSwiZW1haWwiOiJzaGV3ZXRhLnRoYXJhbmlAZm9jYWx3b3Jrcy5pbiIsIm9yaWdfaWF0IjoxNTU3MzExNjQ5fQ.Kfqt0Inwj3pvSkS0_Y8ZMIOkl-eVW1wPKpFgjrfGtWI'
            if token == '':
                log.info('request logged out due to wp cookie not set')
                logout_user = True

            result = {}
            if not logout_user:
                result = verify_usertoken(token)
                if result.has_key('error') or not result.has_key('user'):
                    log.info('request logged out due to token verification failure')
                    logout_user = True

            if not logout_user:
                if result['user'].has_key('email'):
                    wp_user_email = result['user']['email']
                    try:
                    	if not isinstance(request.user, AnonymousUser):
	                        loggedin_user_email = request.user.email
	                        log.info('wp_user_email: '+str(wp_user_email))
	                        log.info('loggedin_user_email: '+str(loggedin_user_email))
	                        if loggedin_user_email != wp_user_email:
	                            log.info('request logged out due to wp session details not matched with openedx session details')
	                            logout(request)
                    except Exception as e:
                        log.info("request error recieving user details from request: "+str(e))

            # if need to logout user then set user_logged_out to True so as to delete cookie as well
            if logout_user:
                self.user_logged_out = True
                log.info('request logging out')
                logout(request)
        return

    def process_response(self, request, response):
        """
        This will verify token from session.
            If session expired then redirect to login page.
            If session not expired then fetch refresh token 
            and set as current token in session attributes.
        """
        if self.user_logged_out:
            log.info('response deleting cookies because request logged out')
            for cookie_name in [settings.EDXMKTG_LOGGED_IN_COOKIE_NAME, settings.EDXMKTG_USER_INFO_COOKIE_NAME]:
                response.delete_cookie(
                    cookie_name.encode('utf-8'), 
                    path='/', 
                    domain=settings.SESSION_COOKIE_DOMAIN
                )
            self.user_logged_out = False
            return response

        if response.status_code != 200 or not self.process_req_resp:
            return response

        if request.path not in self.bypass_req_urls:
            log.info('---------------------RESPONSE-----------------------------')
            log.info(request.path)
            token = ''

            if request.COOKIES.has_key(self.session_cookie_name):
                token = request.COOKIES[self.session_cookie_name]

            # token = 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoiMmY1OWUwZWUtM2NiMy00YzQzLTg0ODktZGRhM2Q4YTAxMzM0IiwidXNlcm5hbWUiOiJ0ZXN0QHRlc3QuY29tIiwiZXhwIjoxNTU2Mjg5NDU0LCJlbWFpbCI6InRlc3RAdGVzdC5jb20iLCJvcmlnX2lhdCI6MTU1NjI4NTg1NH0.CKiRG8Tp3P7Vwa3KF6dZeo1ymY3dMqYvu3qAqwaG8m8'
            if token == '':
                log.info('response logged out due to empty wp token')
                return redirect("/logout")

            result = verify_usertoken(token)
            if result.has_key('error'):
                log.info('response logged out due to token verification failure')
                return redirect("/logout")

            result = refresh_usertoken(token)
            if result.has_key('error') or not result.has_key('token'):
                log.info('response logged out due to token refresh failure')
                return redirect("/logout")

            log.info('response updating wp cookie token with refresh token')
            # Update refresh token in wordpress cookie
            response.set_cookie(
                self.session_cookie_name, 
                result['token'], 
                secure=(settings.SESSION_COOKIE_SECURE or None),
                **self.cookie_settings
            )

            # Set logged in and user info cookie
            try:
                self.cookie_settings = self.get_updated_cookie_settings(request)
                user_info = get_user_info_cookie_data(request)

                if user_info.has_key('username'):
                    if user_info['username'] != '':
                        user_info_cookie_is_secure = request.is_secure()
                        set_user_info = False

                        if request.COOKIES.has_key(settings.EDXMKTG_USER_INFO_COOKIE_NAME):
                            if json.loads(request.COOKIES[settings.EDXMKTG_USER_INFO_COOKIE_NAME])['username'] == '':
                                set_user_info = True

                        log.info('response setting edxloggedin cookie')
                        response.set_cookie(
                            settings.EDXMKTG_LOGGED_IN_COOKIE_NAME.encode('utf-8'), 
                            'true', 
                            secure=None, 
                            **self.cookie_settings
                        )

                        # if not request.COOKIES.has_key(settings.EDXMKTG_USER_INFO_COOKIE_NAME) or set_user_info:
                        log.info('response setting edx-user-info cookie')
                        log.info(user_info)
                        response.set_cookie(
                            settings.EDXMKTG_USER_INFO_COOKIE_NAME.encode('utf-8'), 
                            json.dumps(user_info), 
                            secure=user_info_cookie_is_secure,
                            **self.cookie_settings
                        )
            except Exception as e:
                log.info('Errorrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrr:\n' + str(e))

        return response

