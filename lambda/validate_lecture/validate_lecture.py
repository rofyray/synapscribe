# lambda/validate_lecture.py
import json
import boto3
import os
import requests
from datetime import datetime

s3_client = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
api_gateway_client = None  # Initialized in handler

VLLM_ENDPOINT = os.environ['VLLM_ENDPOINT']
DYNAMODB_TABLE = os.environ['DYNAMODB_TABLE']
API_GATEWAY_ENDPOINT = os.environ['API_GATEWAY_ENDPOINT']

SUPPORTED_FORMATS = ['mp3', 'wav', 'm4a', 'mp4', 'ogg', 'flac', 'webm']
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB

def lambda_handler(event, context):
    """
    Triggered automatically by S3 PutObject event
    """
    global api_gateway_client
    api_gateway_client = boto3.client(
        'apigatewaymanagementapi',
        endpoint_url=f"https://{API_GATEWAY_ENDPOINT}"
    )

    # Parse S3 event
    record = event['Records'][0]
    bucket = record['s3']['bucket']['name']
    s3_key = record['s3']['object']['key']
    file_size = record['s3']['object']['size']

    # Extract lectureId from key (lectures/{lectureId}.ext)
    lecture_id = s3_key.split('/')[1].split('.')[0]

    print(f"Processing lecture: {lecture_id} ({file_size} bytes)")

    try:
        # Get metadata (includes connectionId for notification)
        obj_metadata = s3_client.head_object(Bucket=bucket, Key=s3_key)
        connection_id = obj_metadata['Metadata'].get('connectionId')

        # Step 1: Validate file size
        if file_size > MAX_FILE_SIZE:
            raise ValueError(f"File too large: {file_size/1024/1024:.2f}MB (max: 100MB)")

        # Step 2: Validate format
        ext = s3_key.split('.')[-1].lower()
        if ext not in SUPPORTED_FORMATS:
            raise ValueError(f"Unsupported format: {ext}")

        # Step 3: Save metadata to DynamoDB (simplified - no audio analysis)
        save_lecture_metadata(lecture_id, s3_key, file_size)

        # Step 4: Notify frontend via WebSocket
        if connection_id:
            notify_frontend(connection_id, {
                'type': 'lecture_ready',
                'lectureId': lecture_id,
                'message': 'Lecture uploaded successfully! Ready for questions.',
                's3Key': s3_key,
                'fileSize': file_size
            })

        print(f"Lecture {lecture_id} processed successfully")
        return {'statusCode': 200, 'body': 'Success'}

    except Exception as e:
        error_msg = str(e)
        print(f"Error processing lecture {lecture_id}: {error_msg}")

        # Notify frontend of error
        if connection_id:
            notify_frontend(connection_id, {
                'type': 'lecture_error',
                'lectureId': lecture_id,
                'error': error_msg
            })

        # Save error status to DynamoDB
        save_lecture_metadata(
            lecture_id,
            s3_key,
            file_size,
            status='failed',
            error=error_msg
        )

        return {'statusCode': 500, 'body': error_msg}

def save_lecture_metadata(lecture_id, s3_key, file_size,
                         status='ready', error=None):
    """Save lecture metadata to DynamoDB"""
    table = dynamodb.Table(DYNAMODB_TABLE)

    item = {
        'sessionId': f"lecture-{lecture_id}",  # Use sessionId as primary key
        'lectureId': lecture_id,
        's3Key': s3_key,
        'fileSize': int(file_size),
        'status': status,
        'createdAt': datetime.now().isoformat()
    }

    if error:
        item['errorMessage'] = error

    table.put_item(Item=item)

def notify_frontend(connection_id, message):
    """Send message to frontend via API Gateway WebSocket"""
    try:
        api_gateway_client.post_to_connection(
            ConnectionId=connection_id,
            Data=json.dumps(message).encode('utf-8')
        )
        print(f"Notified connection {connection_id}: {message['type']}")
    except api_gateway_client.exceptions.GoneException:
        print(f"Connection {connection_id} is gone")
    except Exception as e:
        print(f"Error notifying {connection_id}: {e}")
