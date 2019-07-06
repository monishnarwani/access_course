# -*- coding: utf-8 -*-
"""
Database models for access_course.
"""

from __future__ import absolute_import, unicode_literals
from django.conf import settings
from django.contrib.auth.models import User
from django.db import models
from model_utils.models import TimeStampedModel
from six import text_type
from opaque_keys.edx.django.models import CourseKeyField

class  userdetails(models.Model):
    student = models.ForeignKey(User, db_index=True, on_delete=models.CASCADE,unique=True)
    photourl= models.CharField(max_length=2000 ,default=None)
    displayname= models.CharField(max_length=255,default=None)
    external_ref_id = models.CharField(max_length=255,default=None)
    created = models.DateTimeField(auto_now_add=True, db_index=True)
    modified = models.DateTimeField(auto_now=True, db_index=True)
    class Meta(object):
        app_label = "access_course"

class TOCList(models.Model):
    course_id = CourseKeyField(max_length=255, db_index=True)
    unit_name = models.CharField(max_length=255)
    unit_id = models.CharField(max_length=255)
    unit_type=models.CharField(max_length=255)
    created = models.DateTimeField(auto_now_add=True, db_index=True)
    modified = models.DateTimeField(auto_now=True, db_index=True)
    class Meta(object):
        app_label = "access_course"
        unique_together = (('course_id','unit_id'),)

class TOCProgress(models.Model):
    student = models.ForeignKey(User, db_index=True, on_delete=models.CASCADE)
    uuid = models.CharField(max_length=255)
    course_id = CourseKeyField(max_length=255, db_index=True)
    unit_name = models.CharField(max_length=255)
    unit_id = models.CharField(max_length=255)
    status =  models.FloatField(default=0.0)
    created = models.DateTimeField(auto_now_add=True, db_index=True)
    modified = models.DateTimeField(auto_now=True, db_index=True)
    class Meta(object):
        app_label = "access_course"
        unique_together = (('course_id','student','unit_id'),)


class CourseProgress(models.Model):
    uuid=models.CharField(max_length=255)
    student = models.ForeignKey(User, db_index=True, on_delete=models.CASCADE)
    course_id = CourseKeyField(max_length=255, db_index=True)
    start_date= models.DateTimeField()
    end_date= models.DateTimeField()
    total_units=models.PositiveSmallIntegerField()
    units_completed=models.PositiveSmallIntegerField()
    units_inprogress=models.PositiveSmallIntegerField()
    created = models.DateTimeField(auto_now_add=True, db_index=True)
    modified = models.DateTimeField(auto_now=True, db_index=True)

    class Meta(object):
        app_label = "access_course"
        unique_together = (('course_id','student'),)
    
