BUCKET_NAME = "<FRONTEND_BUCKET_NAME>"
CLOUDFRONT_DISTRIBUTION_ID = "<FRONTEND_CLOUDFRONT_ID>"
SECRET_NAME = "<SECRET_NAME>"
SECRET_REGION = "<SECRET_REGION>"

EVENT_ID = "53b5de8d-7b9d-4fcc-a178-6433641075fe"
MAX_RESULT = 25

GET_TOKEN_URL = "https://portal.awsevents.com/config/config.json"
GRAPHQL_URL = "https://api.us-east-1.prod.events.aws.a2z.com/public/graphql"
ATTENDEE_GRAPHQL_URL = "https://api.us-east-1.prod.events.aws.a2z.com/attendee/graphql"

OLD_PUBLIC_SESSIONS_FILE_PATH = "/tmp/old_sessions.json"
PUBLIC_SESSIONS_FILE_PATH = "/tmp/sessions.json"

OBJECT_NAME = "sessions.json"

COGNITO_USERPOOL_ID = "us-east-1_Xuc1O0biz"
COGNITO_CLIENT_ID = "2h40eam2atft40g0c3mlg0aei1"
COGNITO_REGION = "us-east-1"

import hashlib
import sys
sys.path.append('/opt')

import time
import json
import requests
import boto3

from pycognito.utils import RequestsSrpAuth

def get_api_key():
    r = requests.get(GET_TOKEN_URL)
    response = r.json()
    api_key = response["graphqlpublic"]["unauthenticatedApiKey"]
    return api_key

def get_cognito_username_and_password():
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
    api_key = get_api_key()
    cognito_username, cognito_password = get_cognito_username_and_password()

    #######################
    # Get public sessions #
    #######################
    with open("./listPublicSessions.graphql", "r") as f:
        query = f.read()
    
    is_first = True
    next_token = None
    sessions = {}
    payload = {
        "operationName": "listPublicSessions",
        "variables": {
            "input": {
                "eventId": EVENT_ID,
                "maxResults": MAX_RESULT,
            }
        },
        "query": query
    }

    while next_token or is_first:
        if next_token:
            payload["variables"]["input"]["nextToken"] = next_token

        r = requests.post(
            GRAPHQL_URL,
            json = payload,
            headers = {
                "x-api-key": api_key,
            }
        )
        response = r.json()

        for session in response["data"]["listPublicSessions"]["results"]:
            session_id = session["sessionId"]
            sessions[session_id] = session
        
        next_token = response["data"]["listPublicSessions"]["nextToken"]
        is_first = False

    #########################
    # Get attendee sessions #
    #########################
    auth = RequestsSrpAuth(
        username = cognito_username,
        password = cognito_password,
        user_pool_id = COGNITO_USERPOOL_ID,
        client_id = COGNITO_CLIENT_ID,
        user_pool_region = COGNITO_REGION,
    )

    with open("./listAttendeeSessions.graphql", "r") as f:
        query = f.read()
    
    is_first = True
    next_token = None
    payload = {
        "operationName": "listAttendeeSessions",
        "variables": {
            "input": {
                "eventId": EVENT_ID,
                "maxResults": MAX_RESULT,
            }
        },
        "query": query
    }
    
    while next_token or is_first:
        try:
            if next_token:
                payload["variables"]["input"]["nextToken"] = next_token

            r = requests.post(
                ATTENDEE_GRAPHQL_URL,
                json = payload,
                auth = auth
            )
            response = r.json()

            for attendee_session in response["data"]["listAttendeeSessions"]["results"]:
                session_id = attendee_session["sessionId"]

                if session_id in sessions:
                    sessions[session_id]["room"] = attendee_session["room"]
                    sessions[session_id]["venue"] = attendee_session["venue"]
                    sessions[session_id]["capacities"] = attendee_session["capacities"]
            
            next_token = response["data"]["listAttendeeSessions"]["nextToken"]
            is_first = False
        except Exception as e:
            print(e)
            print(r.text)
            next_token = None
            is_first = True

    ################
    # Process data #
    ################
    processed_sessions = []
    for _,(_,session) in enumerate(sessions.items()):
        tracks = session["tracks"] if "tracks" in session and session["tracks"] else []
        
        processed_sessions.append({
            "level": session["level"],
            "name": session["name"],
            "tracks": [{"name": track["name"]} for track in tracks],
            "startTime": session["startTime"],
            "duration": session["duration"],
            "sessionId": session["sessionId"],
            "alias": session["alias"],
            "sessionType": None if "sessionType" not in session else {"name": session["sessionType"]["name"]},
            "description": session["description"],
            "venue": None if ("venue" not in session or not session["venue"]) else {"name": session["venue"]["name"]},
            "room": None if ("room" not in session or not session["room"]) else {"name": session["room"]["name"]},
            "capacities": None if ("capacities" not in session or not session["capacities"]) else {
                "reservableRemaining": session["capacities"]["reservableRemaining"],
                "waitlistRemaining": session["capacities"]["waitlistRemaining"]
            },
        })
    
    ##########################
    # Save session into file #
    ##########################
    with open(PUBLIC_SESSIONS_FILE_PATH, "w") as f:
        f.write(json.dumps(processed_sessions))

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
