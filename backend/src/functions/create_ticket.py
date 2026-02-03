"""
Lambda handler for creating tickets
ENHANCED: Multi-tenant support with orgId
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
    
    Multi-tenant: Tickets are scoped to the user's organization (orgId)
    """
    try:
        user = extract_user_from_event(event)
        
        # Validate user has an organization (except platform admins who can specify one)
        org_id = get_ticket_org_id(user, event)
        if not org_id:
            return create_response(400, {
                'error': 'Organization ID is required. User must belong to an organization to create tickets.'
            })
        
        # Verify user can create tickets in this org
        if not user.can_access_org(org_id):
            return create_response(403, {
                'error': 'You do not have permission to create tickets in this organization'
            })
        
        # Sync user to users table if not exists
        sync_user_to_table(user, org_id)
        
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
            'orgId': org_id,  # Multi-tenant: Associate ticket with organization
            'title': title,
            'description': description,
            'status': 'OPEN',
            'priority': priority,
            'category': body.get('category', 'General'),
            'createdBy': user.user_id,
            'createdByEmail': user.email,
            'createdByName': user.full_name,
            'createdAt': now,
            'updatedAt': now,
            'updatedBy': user.user_id,
            'assignedTo': None,  # Unassigned by default
            'assignedToName': None,
            'tags': body.get('tags', [])
        }
        
        # Save to DynamoDB
        tickets_table.put_item(Item=ticket)
        
        print(f"Created ticket {ticket_id} in org {org_id} by user {user.email}")
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


def get_ticket_org_id(user, event: Dict[str, Any]) -> str:
    """
    Determine the organization ID for the new ticket.
    
    - Platform admins can specify orgId in request body
    - Other users use their own orgId from JWT
    """
    body = {}
    try:
        body = json.loads(event.get('body', '{}'))
    except json.JSONDecodeError:
        pass
    
    # Platform admins can specify a different org
    if user.is_platform_admin and body.get('orgId'):
        return body.get('orgId')
    
    # Everyone else uses their own org
    return user.org_id


def sync_user_to_table(user, org_id: str) -> None:
    """
    Ensures user exists in users table.
    Creates with customer role if not exists.
    This syncs Cognito users to our app database.
    
    Multi-tenant: Associates user with their organization
    """
    try:
        # Check if user exists
        response = users_table.get_item(Key={'userId': user.user_id})
        
        if 'Item' not in response:
            # Create new user record
            now = datetime.now(timezone.utc).isoformat()
            users_table.put_item(Item={
                'userId': user.user_id,
                'email': user.email,
                'firstName': user.given_name or '',
                'lastName': user.family_name or '',
                'role': user.role,
                'orgId': org_id,  # Multi-tenant: Associate user with organization
                'createdAt': now,
                'updatedAt': now
            })
            print(f"Synced new user {user.email} to users table (org: {org_id})")
        else:
            # Update orgId if not set (for existing users)
            existing_user = response['Item']
            if not existing_user.get('orgId') and org_id:
                users_table.update_item(
                    Key={'userId': user.user_id},
                    UpdateExpression='SET orgId = :orgId, updatedAt = :updatedAt',
                    ExpressionAttributeValues={
                        ':orgId': org_id,
                        ':updatedAt': datetime.now(timezone.utc).isoformat()
                    }
                )
                print(f"Updated user {user.email} with orgId: {org_id}")
                
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