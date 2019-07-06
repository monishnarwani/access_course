"""
Course units API forms
"""

from django.core.exceptions import ValidationError
from django.forms import CharField, Form
from opaque_keys import InvalidKeyError
from opaque_keys.edx.keys import CourseKey


class UnitListGetForm(Form):
    """
    A form to validate query parameters in the course list retrieval endpoint
    """
    unit_type = CharField(required=True)
    course_key = CharField(required=True)

    def clean_unit_type(self):
        """
        Ensure a valid `unit_type` was provided.
        """
        unit_type_string = self.cleaned_data['unit_type']
        if unit_type_string not in ['all', 'training']:
            raise ValidationError("Unit type '{}' is not a valid unit type.".format(unicode(unit_type_string)))

        return unit_type_string

    def clean_course_key(self):
        """
        Ensure a valid `course_key` was provided.
        """
        course_key_string = self.cleaned_data['course_key']
        try:
            return CourseKey.from_string(course_key_string)
        except InvalidKeyError:
            raise ValidationError("'{}' is not a valid course key.".format(unicode(course_key_string)))

