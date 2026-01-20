"""
Lambda handler for creating tickets
ENHANCED: Also syncs user to users table on first ticket creation
"""
import json
import uuid
import os
from datetime import datetime, timezone
from typing import Dict, Any
import boto3
from botocore.exceptions import ClientError

from auth import extract_user_from_event

# Initialize DynamoDB
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
tickets_table = dynamodb.Table(os.environ.get('TICKETS_TABLE', 'dev-tickets'))
users_table = dynamodb.Table(os.environ.get('USERS_TABLE', 'dev-users'))


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for POST /tickets
    Creates a new support ticket in DynamoDB
    Also ensures user exists in users table (sync from Cognito)
    """
    try:
        user = extract_user_from_event(event)
        
        # Sync user to users table if not exists
        sync_user_to_table(user)
        
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
        
        ticket = {
            'ticketId': ticket_id,
            'title': title,
            'description': description,
            'status': 'OPEN',
            'priority': priority,
            'category': body.get('category', 'General'),
            'createdBy': user.user_id,
            'createdByEmail': user.email,
            'createdByName': f"{getattr(user, 'given_name', '')} {getattr(user, 'family_name', '')}".strip() or user.email,
            'createdAt': now,
            'updatedAt': now,
            'updatedBy': user.user_id,
            'assignedTo': None,  # Unassigned by default
            'assignedToName': None,
            'tags': body.get('tags', [])
        }
        
        # Save to DynamoDB
        tickets_table.put_item(Item=ticket)
        
        print(f"Created ticket {ticket_id} by user {user.email}")
        return create_response(201, ticket)
        
    except json.JSONDecodeError:
        return create_response(400, {'error': 'Invalid JSON in request body'})
    except ClientError as e:
        error_code = e.response['Error']['Code']
        print(f"DynamoDB error: {error_code} - {e}")
        return create_response(500, {'error': 'Failed to create ticket'})
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return create_response(500, {'error': 'Internal server error'})


def sync_user_to_table(user) -> None:
    """
    Ensures user exists in users table.
    Creates with CUSTOMER role if not exists.
    This syncs Cognito users to our app database.
    """
    try:
        # Check if user exists
        response = users_table.get_item(Key={'userId': user.user_id})
        
        if 'Item' not in response:
            # Create new user record with CUSTOMER role
            now = datetime.now(timezone.utc).isoformat()
            users_table.put_item(Item={
                'userId': user.user_id,
                'email': user.email,
                'firstName': getattr(user, 'given_name', ''),
                'lastName': getattr(user, 'family_name', ''),
                'role': 'CUSTOMER',  # Default role
                'createdAt': now,
                'updatedAt': now
            })
            print(f"Synced new user {user.email} to users table")
    except Exception as e:
        print(f"Warning: Could not sync user to table: {e}")
        # Don't fail ticket creation if user sync fails


def create_response(status_code: int, body: Dict[str, Any]) -> Dict[str, Any]:
    """Create standardized API Gateway response."""
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