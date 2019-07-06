import json
import logging
from django.conf import settings
from django.http import HttpResponse
from django.contrib.auth.models import User
from django.contrib.auth import login as django_login, backends
from django.shortcuts import redirect
from django.views import View
from .validations import get_course_key,get_course_enrollment,get_usage_key
from courseware.access import has_access
from courseware.courses import get_course
from courseware.access_response import StartDateError
from enrollment.data import create_course_enrollment
from .utils import verify_usertoken,create_edx_user,check_subscription
from rest_framework.authentication import SessionAuthentication
from rest_framework_oauth.authentication import OAuth2Authentication
from rest_framework.generics import ListAPIView
from edx_rest_framework_extensions.paginators import NamespacedPageNumberPagination 
from openedx.core.lib.api.view_utils import DeveloperErrorViewMixin, view_auth_classes
from django.core.exceptions import ValidationError
from openedx.features.course_experience.utils import get_course_outline_block_tree
from .api import list_units
from .forms import UnitListGetForm
from .serializers import CourseSerializer
from rest_framework.views import APIView
# from rest_framework.response import Response
from django.http import JsonResponse
from django.db import transaction
from openedx.core.djangoapps.user_api.models import UserRetirementStatus
from social_django.models import UserSocialAuth
from student.models import get_retired_email_by_email, Registration
from openedx.core.djangolib.oauth2_retirement_utils import retire_dot_oauth2_models, retire_dop_oauth2_models
from rest_framework import status, permissions
from six import text_type
from .models import userdetails

import requests

log=logging.getLogger("test")

def accesscompetition(request,course_id,usage_id):
    return _redirect_to_url(request,course_id,usage_id,1)

def accesstraining(request,course_id,usage_id):
    return _redirect_to_url(request,course_id,usage_id,0)

def accesscourse(request,course_id):
    return _redirect_to_url(request,course_id,None,0)

def _get_session_token(request):
    token=None
    session_cookie_name = settings.BOP_CONFIGURATION.get('WRDPRS_COOKIE_NAME', '')
    if session_cookie_name != '':
        if request.COOKIES.has_key(session_cookie_name):
            token = request.COOKIES[session_cookie_name]
    
    return token



def _redirect_to_url(request, course_id,block_id,competition=0 ):
    # try:
    #        print(request.session)
    #        print(request.session.accessed)
    #        print(request.session.modified)
    #        print(request.session.is_empty())
    #        print(request.session.session_key)
    # except:
    #     print("inside except")
    #     pass
    uuid=""
    if course_id is None or course_id == "":
        return HttpResponse("Course is mandatory input")

    token=_get_session_token(request)
    if token is None:
       return HttpResponse("Token doesnot exist")
    
    try:
        course_key = get_course_key(course_id)
        
    except Exception as e:
        return HttpResponse("Course '{}' is not a valid course ".format(course_id), e)
    if block_id:
        try:
            usage_key = get_usage_key(block_id)
            
        except Exception as e:
            return HttpResponse("Block '{}' is not a valid course ".format(block_id), e)
        

    result= verify_usertoken(token)
    print(result)
    if result.has_key('error'):
        return HttpResponse(result['error'])
    #save photourl and display name
    if 'profile_image' in result['user'].keys():
        profileurl= result['user']['profile_image']
    else:
        profileurl=""
    if result['user'].has_key('uuid'):
        external_ref_id=result['user']['uuid']
    # validate if user has subscribed/purchased the course/training for non competition courses
    if not competition and result['user'].has_key('uuid'):
        valid_subscription = check_subscription(result['user']['uuid'],course_id,block_id);
        if valid_subscription.has_key('error'):
           return HttpResponse(valid_subscription['error'])

    if result['user'].has_key('email') and result['user'].has_key('first_name') and result['user'].has_key('last_name'):

        email=result['user']['email']
        firstname=(result['user']['first_name'])[:29]
        lastname=result['user']['last_name'][:29]
        displayname =   result['user']['first_name'] +" "+  result['user']['last_name']
    else:
        return HttpResponse("The information received from login service doesnot contain firstname lastname or email.\n"+str(result))
    
    #if request.session.session_key:
    log.info(profileurl)
    log.info(displayname)
    try:
        user = User.objects.get(email=email)
        status=True
    except User.DoesNotExist:
        status=create_edx_user(email,firstname,lastname)
        if status:
            try:
                user = User.objects.get(email=email)
            except:
                return HttpResponse("The user in not able to create")
        else:
            return HttpResponse("Error in account creation")
    if user:
        try:
            details=userdetails.objects.get(student=user)
            with transaction.atomic():
                details.photourl=profileurl
                # details.displayname= unicode(displayname)
                details.displayname= displayname
                details.external_ref_id = external_ref_id
                details.save()
        except Exception as e:
            try:
                log.info("befoe calling")
                with transaction.atomic():
                    # details = userdetails(student=user,photourl=profileurl,displayname=unicode(displayname))
                    details = userdetails(student=user,photourl=profileurl,displayname=displayname,external_ref_id=external_ref_id)
                    details.save()
                    log.info("calling after saver")
            except Exception as e:
                log.info("Error in adding-updating userdetails",e)
                pass    
    try:
        #log.info(request.session.session_key)
        if request.session.session_key is None:
            django_login(request, user, backends.ModelBackend)
    except Exception as exc:  
            return HttpResponse("Error in login"+str(exc))
    if user.is_authenticated:
        enrol_data=get_course_enrollment(user,course_key)
        if not enrol_data:
            try:
                create_course_enrollment(user.username,course_id,None,True)
            except Exception as e:
                return HttpResponse('User {} was not enrolled to the course {} '.format(user.username,course_id)+ str(e))
    else:
            return HttpResponse('User {} is not logged in '.format(request.user.username)) 
    
    print("before redirect")
    if block_id == None:
        return redirect( '/courses/'+course_id)
    else:
        return redirect('/courses/'+course_id+'/jump_to/'+block_id)
    # return HttpResponse("hi")  


@view_auth_classes(is_authenticated=True)
class UnitListView(DeveloperErrorViewMixin, ListAPIView):

    """
    **Use Case**

        Returns the units for a course

    **Example requests**:

        GET /access_course/v1/units/<course_id>/
        GET /access_course/v1/units/<course_id>/type/<unit_type>/

    **Parameters**:
        * course_id: course id for which units to be returned.
        * unit_type: 'training'
            if training then only units with assessment type as training will be returned.
   
    **Response Values**
        {    "pagination":{"count":7,"previous":null,"num_pages":2,"next":"http://localhost:18000/access_course/v1/units/course-v1:org1+cn1+cr1/?page=2"},
            "results":[
                {"id":<<id>>,
                "course_id":<<course_id>>,
                "block_id":<<block_id>>,
                "block_name":<<block_name>>,
                "block_type":<<block_type>>
                },
                ...
            ]
        }

       The following fields are returned with a successful response.
        
        * id: (string) The ID of the unit block.

        * course_id: (string) The usage ID of the course for which unit list was requested.

        * block_id: (string) The usage ID of the unit block.

        * block_name: (string) The display name of unit block.
        * block_type: (string) The assessment type of unit block if assessment xblock else 'General'. 
            Possible values are:
            'General', 'Training', 'Deep Learning', 'Knowledge Acquisition'

    **Example**

        For all units within a course:

        http://foo.localhost:18000/access_course/v1/units/course-v1:org1+cn1+cr1/

        {    "pagination":{"count":7,"previous":null,"num_pages":2,"next":"http://localhost:18000/access_course/v1/units/course-v1:org1+cn1+cr1/?page=2"},
            "results":[
                {"id":"bffd97d59b604a54af96151814c6d33c",
                "course_id":"course-v1:org1+cn1+cr1",
                "block_id":"block-v1:org1+cn1+cr1+type@vertical+block@bffd97d59b604a54af96151814c6d33c",
                "block_name":"Unit1",
                "block_type":"Knowledge Acquisition"
                },
                {"id":"fc52aca52c2d491f87fa918a86dbf2f0",
                "course_id":"course-v1:org1+cn1+cr1",
                "block_id":"block-v1:org1+cn1+cr1+type@vertical+block@fc52aca52c2d491f87fa918a86dbf2f0",
                "block_name":"Unit2",
                "block_type":"Knowledge Acquisition"
                },
                ...
            ]
        }

        For training units within a course:

        http://foo.localhost:18000/access_course/v1/units/course-v1:org1+cn1+cr1/type/training/

        {    "pagination":{"count":3,"previous":null,"num_pages":1,"next":null},
            "results":[
                {"id":"bd3d26675bd6482c9fd13930c3c6f239",
                "course_id":"course-v1:org1+cn1+cr1",
                "block_id":"block-v1:org1+cn1+cr1+type@vertical+block@bd3d26675bd6482c9fd13930c3c6f239",
                "block_name":"Unit1Training",
                "block_type":"Training"
                },
                {"id":"0d0279f5a87d4e05b33112030a885c3f",
                "course_id":"course-v1:org1+cn1+cr1",
                "block_id":"block-v1:org1+cn1+cr1+type@vertical+block@0d0279f5a87d4e05b33112030a885c3f",
                "block_name":"Unit11",
                "block_type":"Training"
                },
                ...
            ]
        }

    """

    pagination_class = NamespacedPageNumberPagination
    pagination_class.max_page_size = 100
    serializer_class = CourseSerializer
    # authentication_classes = (OAuth2Authentication,
    #                           SessionAuthentication,)

    def get_queryset(self):
        """
        Return a list of course verticals/units(training/all) visible to the user.
        """
        if not self.request.user.is_superuser:
            raise ValidationError("You don't have authority to perform this action")
            
        requested_params = self.request.query_params.copy()
        requested_params.update({'course_key': self.kwargs['course_key_string']})
        # Passing unit_type as 'all' to retrieve all units if unit_type is not already set through endpoint URL.
        requested_params.update({'unit_type': self.kwargs.setdefault('unit_type', 'all')})

        form = UnitListGetForm(requested_params)
        if not form.is_valid():
            raise ValidationError(form.errors)

        units_list = list_units(
            self.request,
            form.cleaned_data['course_key'],
            form.cleaned_data['unit_type'],
        )

        return  [unit for unit in units_list]


class DeactivateAccountView(APIView):
    """
    POST /access_course/user/v1/account/deactivate/
    {
        "email": "test@test.com",
    }

    **POST Parameters**

      A POST request must include the following parameter.

      * email: Required. The email of the user being deactivated.

    **POST Response Values**

     If the request does not specify any access token,
     then request returns below response:
     {  'detail':  'Authentication credentials were not provided.'
     }

     If the request does specify invalid access token,
     then request returns below response:
     {  'detail':  'Invalid token'
     }

     If the request does not specify an email then request returns below response:
     {  'status':   403, 
        'message':  'Mandatory parameter is missing.'
     }

    If the request submits an email for a non-existent user, 
    then request returns below response:
     {  'status':   404, 
        'message':  'Could not verify user email: test@test.com not found.'
     }

     If the specified user is successfully deactivated, the request
     returns below response:
     {  
        'status':   200, 
        'message':  'User deleted successfully.'
     }

     If an unanticipated error occurs, the request returns below response:
     {  'status':   500, 
        'message':  error description
     }

    Allows user with valid access token to take the following actions:
    -  Change the user's password permanently to Django's unusable password
    -  User's exact personal data is vitiated so that it is unusable
    -  Removes the activation keys sent by email to the user for account activation.
    -  Deletes OAuth tokens associated with the user
    -  Create a row in the retirement table for that user so as to indicate the user is no longer active
    
    """
    authentication_classes = (SessionAuthentication, 
                            OAuth2Authentication )
    permission_classes = (permissions.IsAuthenticated, )

    def post(self, request):
        """
        POST /access_course/user/v1/account/deactivate/

        Marks the user as having no password set for deactivation purposes.
        """

        if request.POST.get('email', '') == '':
            return JsonResponse(
                {   'status':   status.HTTP_403_FORBIDDEN, 
                    'message':  'Mandatory parameter is missing.'}
            )

        email = request.POST.get('email')

        try:

            # Get the user from the email
            user = User.objects.get(email=email)
            with transaction.atomic():
                UserRetirementStatus.create_retirement(user)
                # Unlink LMS social auth accounts
                UserSocialAuth.objects.filter(user_id=user.id).delete()
                # Change LMS password & email
                user_email = user.email
                user.email = get_retired_email_by_email(user_email)
                user.save()
                user.set_unusable_password()
                user.save()
                # TODO: Unlink social accounts & change password on each IDA.
                # Remove the activation keys sent by email to the user for account activation.
                Registration.objects.filter(user=user).delete()
                # Add user to retirement queue.
                # Delete OAuth tokens associated with the user.
                retire_dop_oauth2_models(user)
                retire_dot_oauth2_models(user)
                # TODO: send notification to user if needed.

            return JsonResponse(
                {   'status':   status.HTTP_200_OK, 
                    'message':  'User deleted successfully.'}
            )
        except User.DoesNotExist as err:  # pylint: disable=broad-except
            return JsonResponse(
                {   'status':   status.HTTP_404_NOT_FOUND, 
                    'message':  'Could not verify user email: {} not found.'.format(email)}
            )
        except KeyError:
            return JsonResponse(
                {   'status':   status.HTTP_400_BAD_REQUEST, 
                    'message':  'User email not specified.'}
            )
        except Exception as exc:  # pylint: disable=broad-except
            return JsonResponse(
                {   'status':   status.HTTP_500_INTERNAL_SERVER_ERROR, 
                    'message':  text_type(exc)}
            )
