"""
Lambda handler for generating S3 presigned URLs for file uploads
Supports: JPEG, PNG, GIF, PDF files
Endpoint: POST /attachments/upload-url

FILE LOCATION: backend/src/functions/get_upload_url.py
"""
import json
import boto3
import os
from datetime import datetime
import uuid

s3_client = boto3.client('s3')
bucket_name = os.environ.get('ATTACHMENTS_BUCKET')

def handler(event, context):
    """
    Generate a presigned URL for uploading files to S3
    Accepts: image/jpeg, image/png, image/gif, application/pdf
    
    Request body:
    {
        "fileName": "screenshot.png",
        "contentType": "image/png"
    }
    
    Response (200):
    {
        "uploadUrl": "https://s3.amazonaws.com/...",
        "fields": { ... },
        "key": "tickets/2024-01-20T...-uniqueid-screenshot.png"
    }
    """
    try:
        # Parse request body
        body_str = event.get('body', '{}')
        
        # Handle both string and parsed body
        if isinstance(body_str, str):
            body = json.loads(body_str)
        else:
            body = body_str
            
        file_name = body.get('fileName', '').strip()
        content_type = body.get('contentType', '').strip()
        
        print(f"Upload request: fileName={file_name}, contentType={content_type}")
        
        # ===== VALIDATION =====
        
        if not file_name:
            return error_response(400, 'fileName is required')
        
        if not content_type:
            return error_response(400, 'contentType is required')
        
        # ===== ALLOWED FILE TYPES (INCLUDES PNG!) =====
        allowed_types = {
            'image/jpeg': ['.jpg', '.jpeg'],
            'image/png': ['.png'],          # PNG SUPPORT
            'image/gif': ['.gif'],
            'application/pdf': ['.pdf']
        }
        
        if content_type not in allowed_types:
            allowed_str = ', '.join(allowed_types.keys())
            return error_response(
                400, 
                f'File type {content_type} not allowed. Allowed: {allowed_str}'
            )
        
        # ===== VALIDATE FILE EXTENSION MATCHES CONTENT TYPE =====
        
        file_ext = os.path.splitext(file_name)[1].lower()
        
        if file_ext not in allowed_types[content_type]:
            return error_response(
                400,
                f'File extension {file_ext} does not match content type {content_type}. '
                f'For {content_type}, use: {", ".join(allowed_types[content_type])}'
            )
        
        if not file_ext:
            return error_response(400, f'File must have an extension (e.g., .png, .jpg, .pdf)')
        
        # ===== GENERATE UNIQUE S3 KEY =====
        
        unique_id = str(uuid.uuid4())[:8]
        timestamp = datetime.now().isoformat()
        s3_key = f"tickets/{timestamp}-{unique_id}-{file_name}"
        
        print(f"S3 key: {s3_key}")
        
        # ===== GENERATE PRESIGNED URL =====
        
        try:
            presigned_post = s3_client.generate_presigned_post(
                Bucket=bucket_name,
                Key=s3_key,
                Fields={'Content-Type': content_type},
                Conditions=[
                    ['content-length-range', 0, 5242880],  # Max 5MB
                    ['eq', '$Content-Type', content_type]
                ],
                ExpiresIn=3600  # URL valid for 1 hour
            )
            
            print(f"Presigned URL generated successfully")
            
            return success_response({
                'uploadUrl': presigned_post['url'],
                'fields': presigned_post['fields'],
                'key': s3_key,
                'expiresIn': 3600
            })
            
        except Exception as e:
            print(f'Error generating presigned URL: {str(e)}')
            return error_response(500, f'Failed to generate upload URL: {str(e)}')
    
    except json.JSONDecodeError as e:
        print(f'JSON decode error: {str(e)}')
        return error_response(400, f'Invalid JSON in request body: {str(e)}')
    except Exception as e:
        print(f'Unexpected error: {str(e)}')
        return error_response(500, f'Internal server error: {str(e)}')


def success_response(data):
    """Return successful 200 response with CORS headers"""
    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
            'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS'
        },
        'body': json.dumps(data)
    }


def error_response(status_code, message):
    """Return error response with CORS headers"""
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
            'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS'
        },
        'body': json.dumps({
            'error': message,
            'statusCode': status_code
        })
    }