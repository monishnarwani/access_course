# import json
import requests
import string
from requests.exceptions import SSLError
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError
from openedx.core.djangoapps.user_api.accounts.api import create_account,check_account_exists
from django.core.cache import caches
from xmodule.modulestore.django import modulestore
import logging
log = logging.getLogger(__name__)
from opaque_keys.edx.keys import CourseKey, UsageKey
from .models import TOCProgress, CourseProgress
from django.db import transaction
import completion
from completion.models import BlockCompletion
from six import text_type
from openedx.core.djangoapps.user_api.accounts.api import create_account,check_account_exists,activate_account
from django.contrib.auth.hashers import make_password
from django.utils.crypto import get_random_string
from django.conf import settings
import unicodedata
from .models import userdetails
import uuid

progress= {"NOT_STARTED": "Not Started",
           "STARTED": "Started",
           "COMPLETE": "Complete"}


def get_username(user):
    print(user)
    profile=userdetails.objects.filter(student=user)
    if len(profile) > 0:
        displayname=profile[0].displayname
    else:
        displayname=""
    try:
        newname=displayname.encode('latin-1')
    except:
        newname=displayname.encode('utf-8')
    # return displayname.encode('latin-1')
    # return displayname.encode('utf-8')
    return displayname

def get_profileimage(user):
    print(user)
    profile=userdetails.objects.filter(student=user)
    if len(profile) > 0:
        imageurl = profile[0].photourl
    else:
        imageurl= ""
    return imageurl

def _validate_url(url):
    
    val = URLValidator()   
    try:
        val(url)
        return {"status":True,"error":''}
    except ValidationError, e:
        return {"status": False,"error":e}
def validate_uuid(uuid_string):
    try:
        val = uuid.UUID(uuid_string, version=4)
        return True
    except ValueError:
        # If it's a value error, then the string 
        # is not a valid hex code for a UUID.
        return False
        
def send_ab_progress(data_dict):

    if data_dict['uuid']  is None or data_dict['uuid'] =="":
        return "Unique Identifier is mandatory value to send progress.Cannot Send data"
    
    if validate_uuid(data_dict['uuid']) == False:
        return "Unique Identifier is not valid UUID. Cannot send data."

    if data_dict['block_id'] is None or data_dict['block_id'] == '':
        return "Block Id is mandatory value to send progress.Cannot Send data"
    
    if data_dict['course_id'] is None or data_dict['course_id'] == "":
        return "Course Id is mandatory value to send progress.Cannot Send data"

    if data_dict['assessment_type'] is None or data_dict['assessment_type'] == "":
        return "Assessment Type is mandatory value to send progress.Cannot Send data"

    if data_dict['total_problems'] is None or not isinstance(data_dict['total_problems'] ,int):
        return "Total Problems is mandatory integer field.Cannot send data"

    if data_dict['correct'] is None or not isinstance(data_dict['correct'] ,int):
        return "Correct is mandatory integer field.Cannot send data"

    if data_dict['incorrect'] is None or not isinstance(data_dict['incorrect'] ,int):
        return "InCorrect is mandatory integer field.Cannot send data"

    if data_dict['first_attempt'] is None or not isinstance(data_dict['first_attempt'] ,bool):
        return "First Attempt is mandatory Boolean field.Cannot send data"

    if  data_dict['incorrect'] + data_dict['correct']  > data_dict['total_problems']:
        return "The sum of incorrect and correct cannot be greater than total_problems.Cannot Send Data"
    api_course_progress = settings.BOP_CONFIGURATION.get("API_COURSE_PROGRESS", "")
    system_token = settings.BOP_CONFIGURATION.get("SYSTEM_TOKEN", "")
        
    if api_course_progress != "" and system_token!='' :
        input_data= {
        "user_id": data_dict['uuid'],
        "id": data_dict['url_name'],
        "block_id": data_dict['block_id'] ,
        "course_id": data_dict['course_id'],
        "block_name": data_dict['block_name'],
        "block_type": data_dict['assessment_type'],
        "total_problems": data_dict['total_problems'],
        "correct_problems": data_dict['correct'],
        "incorrect_problems": data_dict['incorrect'],
        "is_first_attempt": data_dict['first_attempt'],
        "status": data_dict['status'],
        "start_date": data_dict['start_date'],
        "end_date": data_dict['end_date']
        } 
        header={"Api-Token": system_token}
        result = _get_data_from_url(api_course_progress,header,input_data)
        print result
    else:
        return "The Course Progress API or/and System Token is not set. Cannot Send Data."
    return result    

def send_training_progress(student,course,blk,complete,total_problems,correct,incorrect,first_attempt,start_date,end_date,assessment_type):

    api_course_progress = settings.BOP_CONFIGURATION.get("API_COURSE_PROGRESS", "")
    system_token = settings.BOP_CONFIGURATION.get("SYSTEM_TOKEN", "")
    cache=caches['redis-cache'] 
    try:
        ud=userdetails.objects.get(student=student)
        log.info("The value exist")
        log.info("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
        uuid=    ud.external_ref_id

        header={"Api-Token": system_token}
    except Exception as e:
        print(e)
        log.info("External User Id is not available for student ",student.email)
        return
    store=modulestore()
    block=store.get_item(blk)
    print("@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@2")
    print end_date , len(end_date)
    input_data= {
        "user_id": uuid,
        "id": block.url_name,
        "course_id": text_type(course),
        "block_id": text_type(blk),
        "block_name": block.display_name_with_default,
        "block_type": assessment_type,
        "total_problems": total_problems,
        "correct_problems": correct,
        "incorrect_problems": incorrect,
        "is_first_attempt": first_attempt,
        "status": "In Progress" if complete > 0.0 and complete < 1.0  else  "Completed" if complete == 1.0 else  "Not Started",
        "start_date": "" if start_date is None else start_date,
        "end_date": "" if end_date is None else end_date
    }
    log.info(input_data)
    if api_course_progress != "" and input_data['user_id']!='' :
        result = _get_data_from_url(api_course_progress,header,input_data)
        log.info(result)
        log.info("what did it return")
   

def send_course_progress(details,student,course,blk,complete,xtype):

    api_course_progress = settings.BOP_CONFIGURATION.get("API_COURSE_PROGRESS", "")
    system_token = settings.BOP_CONFIGURATION.get("SYSTEM_TOKEN", "")
    cache=caches['redis-cache'] 
    if  system_token == "":
        return None

    log.info('"""""""""""""""""""""""""""""""""""""'+str(complete))
    input_data={}
    check_for_video =True
    ka_block_status =0.0
    input_status=progress['NOT_STARTED'] 
    KABlockType = False
    with transaction.atomic():
        if details is not None:
            store=modulestore()
            if details.has_key('block_id'):
                
                block=store.get_item(blk)
                input_data['display_name']=block.display_name_with_default
                input_data['id']=block.url_name
                input_data['course_id']=details['course_id']
                input_data['block_id']=details['block_id']
                input_data['status']=progress["NOT_STARTED"]
                print student
                try:
                    ud=userdetails.objects.get(student=student)
                    log.info("The value exist")
                    log.info("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
                    uuid=    ud.external_ref_id
                except Exception as e:
                    print(e)
                    uuid=""
                input_data['user_id']= uuid

        blocks_for_completion=[(child.block_type,store.get_item(child)) for child in block.children if child.block_type == 'assessmentxblock']
        has_assessment_blk=False
        assess_status=progress['NOT_STARTED']
        for blk_type, blk1 in blocks_for_completion:

            if blk_type == 'assessmentxblock':
                has_assessment_blk= True
                usage_key_string=str(blk1.scope_ids.usage_id)
                log.info("usage_key_string"+usage_key_string)
                usage_key = UsageKey.from_string(usage_key_string)
                try:
                    comp=BlockCompletion.objects.get(user=student,course_key=course,block_key=usage_key,block_type="assessmentxblock")         
                    complt=comp.completion
                    
                except Exception as e:
                    log.info(e)
                    complt=0.0
                if (complt > 0.0 and complt < 1.0):
                    log.info("in the progress")
                    assess_status = progress["STARTED"]
                elif complt == 1.0:
                    log.info("in the complete")
                    assess_status = progress["COMPLETE"]
                else:
                    log.info("problem"+str(complt))
                input_data['block_type']= blk1.assessment_type
                input_data['status'] = assess_status

                if (blk1.assessment_type == 'knowledge_acquisition') and input_data['status'] in ( progress['NOT_STARTED'], progress["COMPLETE"]):
                    
                    ka_block_status= complt
                    check_for_video=True 
                    KABlockType=True
                else:
                    check_for_video=False  
        log.info(input_data)            
        video_status = progress["NOT_STARTED"]
        log.info("i am here" + str(check_for_video))
        if (check_for_video==True):
            blocks_for_completion=[(child.block_type,store.get_item(child),child) for child in block.children if child.block_type == 'video' ]
            log.info("Testing")
            for blk_type, blk, ch in blocks_for_completion:
                #id=ch.get("id","")
                log.info("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
                log.info(str(blk.scope_ids.usage_id))
                usage_key_string=str(blk.scope_ids.usage_id)
                log.info("usage_key_string"+usage_key_string)
                usage_key = UsageKey.from_string(usage_key_string)
                #log.info("usage_key=="+type(usage_key)) 
                block_value=store.get_item(usage_key)
                log.info("_______________________________________________________")
                log.info(vars(block_value))
                try:
                    log.info("is this called")
                    comp=BlockCompletion.objects.get(user=student,course_key=course,block_key=usage_key)         
                    log.info("comp.completion:" +str(comp.completion))
                    complt=comp.completion
                except Exception as e:
                    log.info(KABlockType)
                    log.info(ka_block_status)
                    log.info(str(KABlockType == True))
                    log.info(ka_block_status == 1.0)
                    if KABlockType == True and ka_block_status == 1.0:
                        log.info("inside iffffffffffff")
                        try:
                            comp=BlockCompletion(user=student,course_key=course,block_key=usage_key, completion=1.0)
                            comp.save()
                        except Exception as e:
                            log.info("#####################################################33")
                            log.info(e)                           
                        log.info("Save video completion")         
                    complt=complete
                    log.info(e)
                if (complt > 0.0 and complt < 1.0):
                    video_status = progress["STARTED"]
                elif complt == 1.0:
                    video_status = progress["COMPLETE"]    
            # Check for completion status from Video if there is no assessmentxblock or assessmentxblock is started
        log.info("input_data['status']: "+input_data['status'])
        log.info("video_status: "+ video_status)
        if   has_assessment_blk == False:
            input_data['status']=video_status
        elif check_for_video == True and input_data['status'] == progress["NOT_STARTED"] and video_status != progress["NOT_STARTED"]:
            input_data['status'] = progress["STARTED"]  
        if (input_data['status'] == progress['NOT_STARTED']):
            unit_comp=0.0
        elif (input_data['status'] == progress['STARTED']):             
            unit_comp=0.5
        else:
            unit_comp=1.0
        send_data=True
        print(cache)
        if (student.id,text_type(course),input_data['block_id'])  in cache:
            log.info("the cache key exists")

            val=cache.get((student.id,text_type(course),input_data['block_id']))
            if val == unit_comp:
                send_data = False
        if send_data:    
            val=cache.set((student.id,text_type(course),input_data['block_id']),unit_comp)
            log.info("the cache key doesnot exist. So it was set... check redis")
            try:
                tocp=TOCProgress.objects.get(student=student,course_id=course,unit_id=input_data['block_id'])
                if unit_comp == tocp.status:
                    pass
                else:
                    tocp.status=unit_comp
                    tocp.save()
                        
            except:
                tocp=TOCProgress(student=student,course_id=course,unit_id=input_data['block_id'],unit_name=input_data['display_name'],status=unit_comp)
                tocp.save()
                toclist=TOCProgress.objects.filter(student=student,course_id=course)
                if toclist.count() == 1:
                    log.info("first value")
            header={"Api-Token":system_token}
            input_data['created'] = (tocp.created).isoformat()
            input_data['modified']= (tocp.modified).isoformat()
            try:
                print("before check of course progress")
                cp=CourseProgress.objects.get(course_id=course,student=student)
            except Exception as e:
                cp=CourseProgress(course_id=course,student=student,uuid=input_data['user_id'],start_date=tocp.created,total_units=0,units_inprogress=0,units_completed=0)
                print("add new course start")
                cp.save()
                if api_course_progress != "" and input_data['user_id']!='':
                    course_start={"user_id":input_data['user_id'],"start_date": tocp.created.isoformat(),"course_id":text_type(course), "end_date":""}
                    print(course_start)
                    result = _get_data_from_url(api_course_progress,header,course_start)
                    print result

   
            #Send course start information
            log.info(input_data)
            #if api_course_progress != "" and input_data['uuid']!='' :
            #    result = _get_data_from_url(api_course_progress,header,input_data)
            #    print result

    
    return input_data

     
def _get_data_from_url(url,header={},input_data={}, method="POST"):
    
    status_dict=_validate_url(url)
    if status_dict['status'] == False:
        return {"error": status_dict['error']}
    if not isinstance(header,dict):
        return {'error': "header parameter has to be type dict."}
    if not isinstance(input_data,dict):
        return {'error': "input data parameter has to be type dict."}
    output=""
    if method == "POST":
        try:

            response=requests.post(url=url,data=input_data,headers=header,verify=False)
            if response.status_code not in [ 200,201]:
                return  {"error": "URL Returns Error"+ response.text}
            elif response.text != "":
                try:
                    # output=json.loads(response.text)
                    output=response.json()
                except Exception as e:
                    return {'error': "Error during json validation "+ str(e)}

        except Exception as e:
            return {'error': "Error during post url "+ url+str(input_data)+str(header)+ str(e)}
    
    elif method == "GET":
        try:
            response=requests.get(url=url, params=input_data, headers=header)
            if response.status_code != 200:
                return  {"error": "URL Returns Error"+ response.text}
            else:
                try:
                    # output=json.loads(response.text)
                    output=response.json()
                except Exception as e:
                    return {'error': "Error during json validation "+ str(e)}

        except Exception as e:
            return {'error': "Error during get url "+ url+str(input_data)+srt(header)+ str(e)}

    else:
        return {"error": "http methods other than post or get not allowed"}

    return output


def verify_usertoken(token):

    api_token_verify = settings.BOP_CONFIGURATION.get("API_TOKEN_VERIFY", "")
    system_token = settings.BOP_CONFIGURATION.get("SYSTEM_TOKEN", "")

    if api_token_verify == "" or system_token == "":
        return None

    if token is not None:
        header={"Api-Token":system_token}
        input_data={"token": token}
        result = _get_data_from_url(api_token_verify,header,input_data)
        return result


def refresh_usertoken(token):

    api_token_refresh = settings.BOP_CONFIGURATION.get("API_TOKEN_REFRESH", "")
    system_token = settings.BOP_CONFIGURATION.get("SYSTEM_TOKEN", "")

    if api_token_refresh == "" or system_token == "":
        return None

    if token is not None:
        header={"Api-Token": system_token}
        input_data={"token": token}
        result = _get_data_from_url(api_token_refresh,header,input_data)
        return result


def fetch_userdetails(uuid=None):

    api_fetch_userdetails = settings.BOP_CONFIGURATION.get("API_FETCH_USERDETAILS", "")
    system_token = settings.BOP_CONFIGURATION.get("SYSTEM_TOKEN", "")

    if api_fetch_userdetails == "" or system_token == "":
        return None

    if uuid is not None:
        header={"Api-Token": system_token}
        result = _get_data_from_url(api_fetch_userdetails+str(uuid)+"/",header,method="GET")
        return result


def check_subscription(uuid, course_id, block_id=None):
    # validate if product is subscribed/purchased 
    user_details = fetch_userdetails(uuid)

    if user_details == None or user_details.has_key('error'):
        return {"error": "Error in retrieving user detail with uuid {}".format(uuid)}
    
    for products in user_details['product_subscriptions']:
        if products.has_key('ed_x_id'):
           
            # if products['ed_x_id'] == (course_id +'/'):
            if products['ed_x_id'] == course_id:
                # if accessed course is purchased
                if products['product_purchased']:
                    return {}
                # if accessed course is not purchased but training is purchased
                elif block_id != None:
                    for training in products['trainings']:
                        if training.has_key('url'):
                            if block_id in training['url'] and training['state'] == "purchased":
                                return {}
                #else:
	        #     return {}
    if block_id == None:
        return {"error": "User is not subscribed/purchased the course {}".format(course_id)}
    elif block_id != None:
        return {"error": "User is not subscribed/purchased either the course {} or the training {}".format(course_id,block_id)}


def create_edx_user(email,firstname,lastname):

    print("inside create_edx_user")
    
    newfirstname= (firstname.replace(" ","")).replace(".","")
    newlastname= (lastname.replace(" ","")).replace(".","")
    temp_username=newfirstname.strip()+newlastname.strip()
    #temp_username=firstname.strip()+lastname.strip()
    username = unicodedata.normalize('NFKD', temp_username).encode('ASCII', 'ignore')
    password=make_password(None)
    conflicts = check_account_exists(username,email)
    print(conflicts) 
    # if username already exists then modify username and try
    while 'username' in conflicts:
        username += get_random_string(length=5)
        conflicts = check_account_exists(username,email)
    print("with new user name")
    print(username)
    #username.translate({ord(c): None for c in string.whitespace})
    #username=username.replace(" ","")
    #print(username)
    print("@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@")   
    try:
        activation_key=create_account(username,password,email)
        try:
            activate_account(activation_key)
        except Exception as e:
            print(e)
            return False
        return True
    except Exception as e:
        print(e)
        return False

