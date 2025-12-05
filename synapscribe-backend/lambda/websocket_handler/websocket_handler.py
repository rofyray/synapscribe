# lambda/websocket_handler.py
import json
import boto3
import os
from datetime import datetime
import uuid
import requests

s3_client = boto3.client('s3')
api_gateway = boto3.client('apigatewaymanagementapi')
dynamodb = boto3.resource('dynamodb')

AGENTCORE_ENDPOINT = os.environ['AGENTCORE_ENDPOINT']
S3_BUCKET = os.environ['S3_BUCKET']

def lambda_handler(event, context):
    """
    WebSocket handler for all routes
    """
    route_key = event['requestContext']['routeKey']
    connection_id = event['requestContext']['connectionId']

    if route_key == '$connect':
        return handle_connect(connection_id)

    elif route_key == '$disconnect':
        return handle_disconnect(connection_id)

    elif route_key == 'request_upload':
        body = json.loads(event['body'])
        return handle_request_upload(connection_id, body)

    elif route_key == 'query':
        body = json.loads(event['body'])
        return handle_query(connection_id, body)

    elif route_key == 'end_session':
        body = json.loads(event['body'])
        return handle_end_session(connection_id, body)

    else:
        return {'statusCode': 400, 'body': 'Unknown route'}

def handle_connect(connection_id):
    """Handle new WebSocket connection"""
    print(f"New connection: {connection_id}")
    return {'statusCode': 200, 'body': 'Connected'}

def handle_disconnect(connection_id):
    """Handle WebSocket disconnection"""
    print(f"Disconnected: {connection_id}")
    # TODO: Trigger session cleanup if needed
    return {'statusCode': 200, 'body': 'Disconnected'}

def handle_request_upload(connection_id, body):
    """
    Generate presigned URL for S3 upload

    Body: {
        "fileName": str,
        "fileSize": int,
        "duration": int (optional),
        "category": "lecture" | "query"
    }
    """
    file_name = body['fileName']
    file_size = body['fileSize']
    category = body.get('category', 'lecture')

    # Validate
    if file_size > 100 * 1024 * 1024:  # 100MB
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'File too large (max 100MB)'})
        }

    # Generate unique key
    file_id = str(uuid.uuid4())
    ext = file_name.split('.')[-1]

    if category == 'lecture':
        s3_key = f"lectures/{file_id}.{ext}"
        lecture_id = file_id
    else:  # query
        session_id = body.get('sessionId', 'default')
        s3_key = f"queries/{session_id}/{file_id}.{ext}"
        lecture_id = None

    # Generate presigned URL (valid for 15 minutes)
    presigned_url = s3_client.generate_presigned_url(
        'put_object',
        Params={
            'Bucket': S3_BUCKET,
            'Key': s3_key,
            'ContentType': f'audio/{ext}',
            'Metadata': {
                'connectionId': connection_id,
                'uploadedAt': datetime.now().isoformat()
            }
        },
        ExpiresIn=900
    )

    response = {
        'type': 'upload_url',
        'uploadUrl': presigned_url,
        's3Key': s3_key,
        'expiresIn': 900
    }

    if lecture_id:
        response['lectureId'] = lecture_id

    # Send response via WebSocket
    send_to_connection(connection_id, response)

    return {'statusCode': 200, 'body': 'OK'}

def handle_query(connection_id, body):
    """
    Route query to AgentCore

    Body: {
        "sessionId": str,
        "lectureId": str,
        "s3Key": str (query audio path)
    }
    """
    # Forward to AgentCore on EC2
    response = requests.post(
        f"{AGENTCORE_ENDPOINT}/invoke",
        json={
            'type': 'query',
            'sessionId': body['sessionId'],
            'lectureId': body['lectureId'],
            's3Key': body['s3Key'],
            'connectionId': connection_id
        },
        stream=True,  # Stream response
        timeout=120
    )

    # Stream AgentCore response back to frontend via WebSocket
    for line in response.iter_lines():
        if line:
            message = json.loads(line)
            send_to_connection(connection_id, message)

    return {'statusCode': 200, 'body': 'OK'}

def handle_end_session(connection_id, body):
    """
    Trigger session end and batch transcription

    Body: {
        "sessionId": str,
        "lectureId": str
    }
    """
    # Notify AgentCore to end session
    requests.post(
        f"{AGENTCORE_ENDPOINT}/end_session",
        json={
            'sessionId': body['sessionId'],
            'lectureId': body['lectureId']
        },
        timeout=30
    )

    send_to_connection(connection_id, {
        'type': 'session_ended',
        'message': 'Transcript saved to your history'
    })

    return {'statusCode': 200, 'body': 'OK'}

def send_to_connection(connection_id, message):
    """Send message to WebSocket connection"""
    endpoint_url = f"https://{os.environ['API_GATEWAY_ENDPOINT']}"
    api_gateway_client = boto3.client(
        'apigatewaymanagementapi',
        endpoint_url=endpoint_url
    )

    try:
        api_gateway_client.post_to_connection(
            ConnectionId=connection_id,
            Data=json.dumps(message).encode('utf-8')
        )
    except api_gateway_client.exceptions.GoneException:
        print(f"Connection {connection_id} is gone")
    except Exception as e:
        print(f"Error sending to {connection_id}: {e}")
