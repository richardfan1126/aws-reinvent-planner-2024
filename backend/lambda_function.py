BUCKET_NAME = "<FRONTEND_BUCKET_NAME>"
CLOUDFRONT_DISTRIBUTION_ID = "<FRONTEND_CLOUDFRONT_ID>"
SECRET_NAME = "<SECRET_NAME>"
SECRET_REGION = "<SECRET_REGION>"

OLD_PUBLIC_SESSIONS_FILE_PATH = "/tmp/old_sessions.json"
PUBLIC_SESSIONS_FILE_PATH = "/tmp/sessions.json"

OBJECT_NAME = "sessions.json"

COGNITO_USERPOOL_ID = "us-east-1_iu3YTdfT3"
COGNITO_CLIENT_ID = "4mbpjh0cd78jbbu5kc5i9717v"
COGNITO_REGION = "us-east-1"

SESSION_STORAGE_URL = "https://28ym3tywek.execute-api.us-east-1.amazonaws.com/storage"
AUTH_CHALLENGE_URL = "https://register.reinvent.awsevents.com/auth/challenge?auth_type=login"
AUTH_LOGIN_URL = "https://register.reinvent.awsevents.com/auth/login/"
COGNITO_LOGIN_URL = "https://hub.reinvent.awsevents.com/auth/login/cognito/"

SESSION_LIST_URL = "https://hub.reinvent.awsevents.com/attendee-portal-api/sessions/list/"

import sys
sys.path.append('/opt')

import hashlib
import re
import time
import json
import requests
import boto3
from botocore.config import Config
from pycognito.aws_srp import AWSSRP

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
    cognito_username, cognito_password = get_username_and_password()

    ################
    # Get sessions #
    ################
    session = requests.Session()
    r = session.get(
        AUTH_CHALLENGE_URL
    )

    regex = r"authorization_code=([^&]+)"
    matches = re.findall(regex, r.url)
    authorization_code = matches[0]

    regex = r"state=([^&]+)"
    matches = re.findall(regex, r.url)
    state = matches[0]

    boto3_config = Config(region_name = COGNITO_REGION)
    client = boto3.client('cognito-idp', config = boto3_config)
    aws_srp = AWSSRP(
        username = cognito_username,
        password = cognito_password,
        pool_id = COGNITO_USERPOOL_ID,
        client_id = COGNITO_CLIENT_ID,
        client = client
    )
    tokens = aws_srp.authenticate_user()

    access_token = tokens["AuthenticationResult"]["AccessToken"]
    id_token = tokens["AuthenticationResult"]["IdToken"]
    refresh_token = tokens["AuthenticationResult"]["RefreshToken"]

    r = session.post(
        SESSION_STORAGE_URL,
        json = {
            "access_token": access_token,
            "id_token": id_token,
            "refresh_token": refresh_token,
            "authorization_code": authorization_code
        }
    )

    r = session.get(
        AUTH_LOGIN_URL,
        params = {
            "code": authorization_code,
            "state": state
        }
    )

    regex = r"authorization_code=([^&]+)"
    matches = re.findall(regex, r.url)
    cognito_authorization_code = matches[0]

    regex = r"state=([^&]+)"
    matches = re.findall(regex, r.url)
    cognito_state = matches[0]

    r = session.post(
        SESSION_STORAGE_URL,
        json = {
            "access_token": access_token,
            "id_token": id_token,
            "refresh_token": refresh_token,
            "authorization_code": cognito_authorization_code
        }
    )

    r = session.get(
        COGNITO_LOGIN_URL,
        params = {
            "code": cognito_authorization_code,
            "state": cognito_state
        }
    )

    r = session.get(
        SESSION_LIST_URL,
    )
    response = r.json()

    extracted_sessions = []

    for session in response["data"]:
        level = ""
        topics = []

        for tag in session["tags"]:
            parent_tag_name = tag["parentTagName"]
            tag_name = tag["tagName"]

            if parent_tag_name == 'Level':
                level = tag_name
            elif parent_tag_name == 'Topic':
                topics.append(tag_name)
        
        remaining_seat = 0
        try:
            remaining_seat = session["sessionCap"] - session["personalAgendaCount"]
        except:
            pass
            
        extracted_sessions.append({
            "level": level,
            "name": session["title"],
            "topics": topics,
            "startTime": session["startDateTime"],
            "endTime": session["endDateTime"],
            "sessionId": session["scheduleUid"],
            "alias": session["thirdPartyID"],
            "sessionType": session["trackName"],
            "description": session["description"],
            "venue": session["venueName"],
            "room": session["locationName"],
            "capacities": {
                "reservableRemaining": remaining_seat,
                "waitlistRemaining": ""
            }
        })

    ##########################
    # Save session into file #
    ##########################
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
