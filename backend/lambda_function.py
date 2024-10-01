BUCKET_NAME = "<FRONTEND_BUCKET_NAME>"
CLOUDFRONT_DISTRIBUTION_ID = "<FRONTEND_CLOUDFRONT_ID>"
SECRET_NAME = "<SECRET_NAME>"
SECRET_REGION = "<SECRET_REGION>"

OLD_PUBLIC_SESSIONS_FILE_PATH = "/tmp/old_sessions.json"
PUBLIC_SESSIONS_FILE_PATH = "/tmp/sessions.json"

OBJECT_NAME = "sessions.json"

LOGIN_URL = "https://registration.awsevents.com/flow/processLogin"
WORKFLOW_API_TOKEN = "awsevents.reinvent24.reg"

LOAD_PAGE_URL = "https://registration.awsevents.com/flow/loadPage"
LOAD_PAGE_PARAMS = {
    "pageUri": "portal",
    "overrideShowDate": "false",
    "workflowApiToken": "awsevents.reinvent24.attendee-portal",
    "ver": "2.1.20240802162547.b8ee5c8b9"
}

SESSION_SEARCH_URL = "https://catalog.awsevents.com/api/search"
SESSION_SEARCH_PAGE_SIZE = 100

import sys
sys.path.append('/opt')

import hashlib
import time
import json
import requests
import boto3

def get_username_and_password():
    client = boto3.client(
        service_name = 'secretsmanager',
        region_name = SECRET_REGION,
    )

    get_secret_value_response = client.get_secret_value(
        SecretId = SECRET_NAME
    )
    
    secret_data = json.loads(get_secret_value_response['SecretString'])
    username = secret_data["USERNAME"]
    password = secret_data["PASSWORD"]

    return (username, password)

def get_sessions():
    username, password = get_username_and_password()

    ################
    # Get sessions #
    ################
    session = requests.Session()

    r = session.post(
        LOGIN_URL,
        data = {
            "email": username,
            "password": password,
            "workflowApiToken": WORKFLOW_API_TOKEN,
        }
    )

    r = session.get(
        LOAD_PAGE_URL,
        params = LOAD_PAGE_PARAMS,
    )

    response = r.json()
    api_profile_token = response["data"]["widgetConf"]["apiProfileToken"]

    current_from = 0
    extracted_sessions = []

    while True:
        r = session.post(
            SESSION_SEARCH_URL,
            data = {
                "type": "session",
                "catalogDisplay": "list",
                "size": SESSION_SEARCH_PAGE_SIZE,
                "from": current_from,
            },
            headers = {
                "rfapiprofileid": api_profile_token
            }
        )

        response = r.json()

        if "sectionList" in response:
            response = response["sectionList"][0]

        for event_session in response["items"]:
            level = ""
            topics = []
            areas_of_interest = []
            industries = []
            roles = []
            services = []

            for attribute in event_session["attributevalues"]:
                attribute_id = attribute["attribute_id"]
                attribute_value = attribute["value"]

                if attribute_id == 'Level':
                    level = attribute_value
                elif attribute_id == 'Topic':
                    topics.append(attribute_value)
                elif attribute_id == 'Areaofinterest':
                    areas_of_interest.append(attribute_value)
                elif attribute_id == 'Industry':
                    industries.append(attribute_value)
                elif attribute_id == 'Role':
                    roles.append(attribute_value)
                elif attribute_id == 'Services':
                    services.append(attribute_value)
            
            # remaining_seat = 0
            # try:
            #     remaining_seat = event_session["sessionCap"] - event_session["personalAgendaCount"]
            # except:
            #     pass

            startTime = ""
            endTime = ""

            if 'times' in event_session and len(event_session['times']) > 0 and 'utcStartTime' in event_session['times'][0]:
                startTime = event_session['times'][0]['utcStartTime']

            if 'times' in event_session and len(event_session['times']) > 0 and 'utcEndTime' in event_session['times'][0]:
                endTime = event_session['times'][0]['utcEndTime']
            
            venue = ""
            if 'times' in event_session and len(event_session['times']) > 0 and 'room' in event_session['times'][0]:
                venue = str(event_session['times'][0]['room'])
                venue = venue.split("|")[0].strip()
                
            extracted_sessions.append({
                "level": level,
                "name": event_session["title"],
                "topics": topics,
                "areasOfInterest": areas_of_interest,
                "industries": industries,
                "roles": roles,
                "services": services,
                "startTime": startTime,
                "endTime": endTime,
                "sessionId": event_session["sessionID"],
                "alias": event_session["code"],
                "sessionType": event_session["type"],
                "description": event_session["abstract"],
                "venue": venue,
                # "room": event_session["locationName"],
                # "capacities": {
                #     "reservableRemaining": remaining_seat,
                #     "waitlistRemaining": ""
                # }
            })

        current_from = response["from"]
        num_items = response["numItems"]
        total = response["total"]

        if current_from + num_items >= total:
            break
        else:
            current_from = current_from + num_items

    # ##########################
    # # Save session into file #
    # ##########################
    with open(PUBLIC_SESSIONS_FILE_PATH, "w") as f:
        f.write(json.dumps({
            "updated": int(time.time()),
            "sessions": extracted_sessions
        }))

def upload_to_s3():
    s3_client = boto3.client('s3')
    cloudfront_client = boto3.client('cloudfront')

    file_changed = True
    try:
        s3_client.download_file(BUCKET_NAME, OBJECT_NAME, OLD_PUBLIC_SESSIONS_FILE_PATH)
        
        with open(OLD_PUBLIC_SESSIONS_FILE_PATH, "r") as f:
            old_file_content = f.read()
        
        with open(PUBLIC_SESSIONS_FILE_PATH, "r") as f:
            new_file_content = f.read()

        old_hash = hashlib.sha512(bytes(old_file_content, "utf-8")).digest().hex()
        new_hash = hashlib.sha512(bytes(new_file_content, "utf-8")).digest().hex()

        if old_hash == new_hash:
            file_changed = False
    except:
        pass
    
    if file_changed:
        s3_client.upload_file(PUBLIC_SESSIONS_FILE_PATH, BUCKET_NAME, OBJECT_NAME, ExtraArgs={
            "ContentType": "application/json"
        })

        cloudfront_client.create_invalidation(
            DistributionId = CLOUDFRONT_DISTRIBUTION_ID,
            InvalidationBatch={
                'Paths': {
                    'Quantity': 1,
                    'Items': [
                        '/sessions.json',
                    ]
                },
                'CallerReference': str(time.time())
            }
        )

def lambda_handler(event, context):
    get_sessions()
    upload_to_s3()

    return True
