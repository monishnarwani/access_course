
import pytest
from django.test.utils import override_settings
from django.test import  TestCase
from django.conf import settings
from access_course.utils import send_ab_progress
"""
To run the script on
devstack  py.test /edx/src/edx_training/access_course/access_course/tests/tests.py
prodstack py.test /openedx/requirements/edx_training/access_course/access_course/tests/tests.py
"""
test_data= [({'uuid': "aefbecef-4fe9-4531-80b0-a595db1c38ce",'url_name':"dd687795ae07459f953eebdd0eaccb1c",'block_id': "block-v1:FW+FW201+2019_BO+type@assessmentxblock+block@035e713abfe74e0bb17751932738276a" , 'course_id': "course-v1:FW+FW201+2019_BO",'block_name': "Unit",'assessment_type':"cme_test","total_problems": 4, "correct":0 , "incorrect":0, 'first_attempt':True,'status': "Not Started", "start_date": "",  "end_date":""}, {}),
 ({'uuid': "",'url_name':"dd687795ae07459f953eebdd0eaccb1c",'block_id': "block-v1:FW+FW201+2019_BO+type@assessmentxblock+block@035e713abfe74e0bb17751932738276a" , 'course_id': "course-v1:FW+FW201+2019_BO",'block_name': "Unit", 'assessment_type':"cme_test","total_problems": 4, "correct":0 , "incorrect":0, 'first_attempt':True,'status': "Not Started", "start_date": "",  "end_date":""},"Unique Identifier is mandatory value to send progress.Cannot Send data"),
 ({'uuid': "aefbecef-4fe9-4531-80b0-a595db1c38ce",'url_name':"dd687795ae07459f953eebdd0eaccb1c",'block_id': "" , 'course_id': "course-v1:FW+FW201+2019_BO",'block_name': "Unit",'assessment_type':"cme_test","total_problems": 4, "correct":0 , "incorrect":0, 'first_attempt':True,'status': "Not Started", "start_date": "",  "end_date":""},"Block Id is mandatory value to send progress.Cannot Send data"),
 ({'uuid': "aefbecef-4fe9-4531-80b0-a595db1c38ce",'url_name':"dd687795ae07459f953eebdd0eaccb1c",'block_id': "block-v1:FW+FW201+2019_BO+type@assessmentxblock+block@035e713abfe74e0bb17751932738276a" , 'course_id': "",'block_name': "Unit",'assessment_type':"cme_test","total_problems": 4, "correct":0 , "incorrect":0, 'first_attempt':True,'status': "Not Started", "start_date": "",  "end_date":""}, "Course Id is mandatory value to send progress.Cannot Send data"),
 ({'uuid': "aefbecef-4fe9-4531-80b0-a595db1c38ce",'url_name':"dd687795ae07459f953eebdd0eaccb1c",'block_id': "block-v1:FW+FW201+2019_BO+type@assessmentxblock+block@035e713abfe74e0bb17751932738276a" , 'course_id': "course-v1:FW+FW201+2019_BO",'block_name': "Unit",'assessment_type':"","total_problems": 4, "correct":0 , "incorrect":0, 'first_attempt':True,'status': "Not Started", "start_date": "",  "end_date":""}, "Assessment Type is mandatory value to send progress.Cannot Send data"),
 ({'uuid': "aefbecef-4fe9-4531-80b0-a595db1c38ce",'url_name':"dd687795ae07459f953eebdd0eaccb1c",'block_id': "block-v1:FW+FW201+2019_BO+type@assessmentxblock+block@035e713abfe74e0bb17751932738276a" , 'course_id': "course-v1:FW+FW201+2019_BO",'block_name': "Unit",'assessment_type':"cme_test","total_problems": "e", "correct":0 , "incorrect":0, 'first_attempt':True,'status': "Not Started", "start_date": "",  "end_date":""}, "Total Problems is mandatory integer field.Cannot send data"),
 ({'uuid': "aefbecef-4fe9-4531-80b0-a595db1c38ce",'url_name':"dd687795ae07459f953eebdd0eaccb1c",'block_id': "block-v1:FW+FW201+2019_BO+type@assessmentxblock+block@035e713abfe74e0bb17751932738276a" , 'course_id': "course-v1:FW+FW201+2019_BO",'block_name': "Unit",'assessment_type':"cme_test","total_problems": 4, "correct":"e" , "incorrect":0, 'first_attempt':True,'status': "Not Started", "start_date": "",  "end_date":""}, "Correct is mandatory integer field.Cannot send data"),
 ({'uuid': "aefbecef-4fe9-4531-80b0-a595db1c38ce",'url_name':"dd687795ae07459f953eebdd0eaccb1c",'block_id': "block-v1:FW+FW201+2019_BO+type@assessmentxblock+block@035e713abfe74e0bb17751932738276a" , 'course_id': "course-v1:FW+FW201+2019_BO",'block_name': "Unit",'assessment_type':"cme_test","total_problems": 4, "correct":0 , "incorrect":"1", 'first_attempt':True,'status': "Not Started", "start_date": "",  "end_date":""}, "InCorrect is mandatory integer field.Cannot send data"),
 ({'uuid': "aefbecef-4fe9-4531-80b0-a595db1c38ce",'url_name':"dd687795ae07459f953eebdd0eaccb1c",'block_id': "block-v1:FW+FW201+2019_BO+type@assessmentxblock+block@035e713abfe74e0bb17751932738276a" , 'course_id': "course-v1:FW+FW201+2019_BO",'block_name': "Unit",'assessment_type':"cme_test","total_problems": 4, "correct":6 , "incorrect":3, 'first_attempt':True,'status': "Not Started", "start_date": "",  "end_date":""}, "The sum of incorrect and correct cannot be greater than total_problems.Cannot Send Data")
]

@pytest.mark.parametrize("test_input, expected_output",test_data)
def test_send_training_progress(test_input,expected_output):
    assert send_ab_progress(test_input) == expected_output

