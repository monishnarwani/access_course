# -*- coding: utf-8 -*-
"""
URLs for access_course.
"""
from __future__ import absolute_import, unicode_literals
from django.conf import settings
from django.conf.urls import url
from django.views.generic import TemplateView
from .views import accesscourse,accesstraining,accesscompetition,UnitListView,DeactivateAccountView

urlpatterns = [

    url(r'^user/v1/account/deactivate/$', DeactivateAccountView.as_view(), name='deactivate_account'),

    url(r'^v1/units/{course_key}/$'.format(
            course_key=settings.COURSE_KEY_PATTERN,
            ), UnitListView.as_view(), name='unit-list'),

    url(r'^v1/units/{course_key}/type/{unit_type}/$'.format(
            course_key=settings.COURSE_KEY_PATTERN,
            unit_type='(?P<unit_type>[a-z]+)'
            ), UnitListView.as_view(), name='training-list'),

    url(r'^competition/{course_key}/{usage_key}/$'.format(
            course_key=settings.COURSE_ID_PATTERN,
            usage_key=settings.USAGE_ID_PATTERN, ), accesscompetition, name='access_competition'),

    
    url(r'^course/{course_key}/training/{usage_key}/$'.format(
            course_key=settings.COURSE_ID_PATTERN,
            usage_key=settings.USAGE_ID_PATTERN, ), accesstraining, name='access_training'),
    
    url(r'^course/{course_key}/$'.format(
             course_key=settings.COURSE_ID_PATTERN,
         ), accesscourse, name='access_course'),
    
    #url(r'^health, health, name='health'),

         
    url(r'', TemplateView.as_view(template_name="access_course/base.html")),
     
   
]
