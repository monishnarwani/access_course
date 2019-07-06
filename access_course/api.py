"""
Course API
"""
from django.core.exceptions import ValidationError
from xmodule.modulestore.django import modulestore
from xmodule.modulestore.exceptions import ItemNotFoundError
from opaque_keys.edx.keys import UsageKey
from openedx.features.course_experience.utils import get_course_outline_block_tree

def list_units(request, course_id, requested_unit_type):
    """
    Return a list of available units within the course.

    Arguments:
        request (HTTPRequest):
            Used to identify the logged-in user and to instantiate the course
            module to retrieve the course about description
        course_id (string):
            Used to extract the sections/subsections/verticals i.e. units within a course
        requested_unit_type (string):
            Used to extract training or all type of units from a course

    Return value:
        List of objects representing the collection of units from a course.
    """

    valid_assessment_types = {'knowledge_acquisition': 'Knowledge Acquisition', 
        'training': 'Training', 
        'deep_learning': 'Deep Learning'}
    course_struct = []
    unit_list = []
    course_id = unicode(course_id)
    requested_unit_type = unicode(requested_unit_type)
    store = modulestore()
    
    try:
        blocks = get_course_outline_block_tree(request, course_id)
    except ItemNotFoundError:
        raise ValidationError("Course '{}' is not a valid course.".format(unicode(course_id)))

    course_name = blocks.get('display_name')
    course_sections = blocks.get('children')

    if course_sections is not None:
        for section in course_sections:
            for subsection in section.get('children', []):
                subchapter_name = subsection.get('display_name')
                for vertical in subsection.get('children', []):
                    # Default block/assessment type set to General
                    block_type = 'General'
                    for childblock in vertical.get('children', []):
                        if childblock.get('type', '').lower() == 'assessmentxblock':
                            childid = childblock.get('id', '')
                            if childid != "":
                                try:
                                    block_usage_key = UsageKey.from_string(childid)
                                    block = store.get_item(block_usage_key)
                                    if block.assessment_type in valid_assessment_types.keys():
                                        block_type = valid_assessment_types[block.assessment_type]
                                        break 
                                    else:
                                        continue
                                except InvalidKeyError:
                                    raise ValidationError("Id {} of assessmentxblock is not a valid usage key.".format(unicode(childid)))
                                except ItemNotFoundError:
                                    raise ValidationError("UsageKey {} of assessmentxblock not found.".format(unicode(block_usage_key)))
                    # if requested all units then simple append unit_list and return unit_list 
                    if requested_unit_type == 'all':
                        unit_list.append({
                                'id': vertical['block_id'], 
                                # 'course_id': course_id,
                                'block_id': vertical['id'],
                                'block_name': vertical['display_name'], 
                                'block_type': block_type
                            })
                    else:
                    # if requested only training units then filter by block_type and then append unit_list and return unit_list
                        if requested_unit_type in block_type.lower():
                            unit_list.append({
                                    'id': vertical['block_id'], 
                                    # 'course_id': course_id,
                                    'block_id': vertical['id'],
                                    'block_name': vertical['display_name'], 
                                    'block_type': block_type
                                })
                if len(unit_list) != 0:
                    course_struct.append({
                        'course_id': course_id,
                        'course_name': course_name,
                        'subchapter_name': subchapter_name,
                        'units': unit_list
                        })
                    unit_list = []

    return course_struct
