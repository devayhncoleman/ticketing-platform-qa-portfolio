"""
Lambda function handler for creating tickets.
FIXED VERSION - handles GSI requirements properly
"""
import json
import uuid
import os
from datetime import datetime, timezone
from typing import Dict, Any
import boto3
from botocore.exceptions import ClientError


# Initialize DynamoDB (connection reuse across Lambda invocations)
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
table_name = os.environ.get('TICKETS_TABLE_NAME', 'dev-tickets')
table = dynamodb.Table(table_name)


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for POST /tickets
    Creates a new support ticket in DynamoDB
    
    Args:
        event: API Gateway event with ticket data in body
        context: Lambda context
    
    Returns:
        API Gateway response with created ticket
    """
    try:
        # Parse request body
        body = json.loads(event.get('body', '{}'))
        
        # Validate required fields
        title = body.get('title', '').strip()
        description = body.get('description', '').strip()
        
        if not title:
            return create_response(400, {'error': 'Title is required'})
        
        if not description:
            return create_response(400, {'error': 'Description is required'})
        
        # Validate priority
        priority = body.get('priority', 'MEDIUM').upper()
        valid_priorities = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']
        if priority not in valid_priorities:
            return create_response(400, {
                'error': f'Invalid priority. Must be one of: {", ".join(valid_priorities)}'
            })
        
        # Create ticket object
        ticket_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        user_id = extract_user_id(event)
        
        ticket = {
            'ticketId': ticket_id,
            'title': title,
            'description': description,
            'status': 'OPEN',
            'priority': priority,
            'category': body.get('category', 'General'),
            'createdBy': user_id,
            'createdAt': now,
            'updatedAt': now,
            'updatedBy': user_id,
            'assignedTo': body.get('assignedTo', 'UNASSIGNED'),  # ✅ Fixed: Default value
            'tags': body.get('tags', [])
        }
        
        # Save to DynamoDB
        table.put_item(Item=ticket)
        
        print(f"✅ Created ticket: {ticket_id} in DynamoDB table: {table_name}")
        
        return create_response(201, ticket)
        
    except json.JSONDecodeError:
        return create_response(400, {'error': 'Invalid JSON in request body'})
    
    except ClientError as e:
        error_code = e.response['Error']['Code']
        print(f"❌ DynamoDB error: {error_code} - {e}")
        return create_response(500, {'error': 'Failed to create ticket'})
    
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")
        return create_response(500, {'error': 'Internal server error'})


def extract_user_id(event: Dict[str, Any]) -> str:
    """
    Extract user ID from JWT token in event
    For now, returns test user ID
    TODO: Implement real JWT parsing when Cognito is set up
    """
    return event.get('requestContext', {}).get('authorizer', {}).get('claims', {}).get('sub', 'test-user-123')


def create_response(status_code: int, body: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create standardized API Gateway response
    """
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,Authorization',
            'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS'
        },
        'body': json.dumps(body, default=str)
    }