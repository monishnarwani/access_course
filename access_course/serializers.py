"""
Course Unit API Serializers.  Representing course unit catalog data
"""

from rest_framework import serializers


class UnitSerializer(serializers.Serializer):  
    """
    Serializer for Course Unit objects providing minimal data about the course unit.
    """

    id = serializers.CharField(read_only=True)  
    # course_id = serializers.CharField(read_only=True)
    block_id = serializers.CharField(read_only=True)  
    block_name = serializers.CharField(read_only=True)
    block_type = serializers.CharField(read_only=True)


class CourseSerializer(serializers.Serializer):
    """
    Serializer for Course
    """
    course_id = serializers.CharField(read_only=True)
    course_name = serializers.CharField(read_only=True)
    subchapter_name = serializers.CharField(read_only=True)
    units = UnitSerializer(many=True, read_only=True)
