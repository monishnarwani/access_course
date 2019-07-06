from opaque_keys import InvalidKeyError
from opaque_keys.edx.keys import CourseKey, UsageKey
from django.core.exceptions import ValidationError
from student.models import CourseEnrollment



def get_course_key(course_key_string):
    
    try:
       return CourseKey.from_string(course_key_string)
    except InvalidKeyError:
       raise ValidationError("'{}' is not a valid course key.".format(unicode(course_key_string)))

def get_usage_key(usage_key_string):
    
    try:
       return UsageKey.from_string(usage_key_string)
    except InvalidKeyError:
       raise ValidationError("'{}' is not a valid usage key.".format(unicode(usage_key_string)))

def get_course_enrollment(user, course_key):
    """Retrieve an object representing all aggregated data for a user's course enrollment.

    Get the course enrollment information for a specific user and course.

    Returns:
        A serializable dictionary representing the course enrollment.

    """
    
    try:
        enrollment = CourseEnrollment.objects.get(
            user=user, course_id=course_key
        )
        return enrollment
    except CourseEnrollment.DoesNotExist:
        return None
