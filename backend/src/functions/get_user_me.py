"""
Lambda handler for getting current user's profile
ENHANCED: Multi-tenant support - includes orgId in response
"""
import json
import os
from datetime import datetime, timezone
from typing import Dict, Any
import boto3
from botocore.exceptions import ClientError

from auth import extract_user_from_event

# Initialize DynamoDB
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
users_table = dynamodb.Table(os.environ.get('USERS_TABLE', 'dev-users'))
organizations_table = dynamodb.Table(os.environ.get('ORGANIZATIONS_TABLE', 'dev-organizations'))


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for GET /users/me
    Returns the authenticated user's profile information
    
    Multi-tenant: Includes organization information if user belongs to one
    
    Response includes:
    - User profile from database (or created if not exists)
    - Organization details (if user belongs to one)
    - Role and permissions context
    """
    try:
        user = extract_user_from_event(event)
        
        # Try to get user from database
        response = users_table.get_item(Key={'userId': user.user_id})
        
        if 'Item' in response:
            user_data = response['Item']
            # Update with latest info from token if changed
            user_data = sync_user_data(user, user_data)
        else:
            # Create new user record
            user_data = create_user_record(user)
        
        # Get organization details if user belongs to one
        org_data = None
        org_id = user_data.get('orgId') or user.org_id
        if org_id:
            org_data = get_organization(org_id)
        
        # Build response
        profile = {
            'userId': user_data.get('userId'),
            'email': user_data.get('email'),
            'firstName': user_data.get('firstName', ''),
            'lastName': user_data.get('lastName', ''),
            'fullName': f"{user_data.get('firstName', '')} {user_data.get('lastName', '')}".strip() or user_data.get('email'),
            'role': user_data.get('role', 'customer'),
            'orgId': org_id,
            'organization': org_data,
            'permissions': get_user_permissions(user),
            'createdAt': user_data.get('createdAt'),
            'updatedAt': user_data.get('updatedAt')
        }
        
        print(f"User {user.email} retrieved their profile")
        return create_response(200, profile)
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        print(f"DynamoDB error: {error_code} - {e}")
        return create_response(500, {'error': 'Failed to retrieve user profile'})
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return create_response(500, {'error': 'Internal server error'})


def create_user_record(user) -> Dict[str, Any]:
    """Create a new user record in the database."""
    now = datetime.now(timezone.utc).isoformat()
    
    user_data = {
        'userId': user.user_id,
        'email': user.email,
        'firstName': user.given_name or '',
        'lastName': user.family_name or '',
        'role': user.role,
        'orgId': user.org_id,
        'createdAt': now,
        'updatedAt': now
    }
    
    users_table.put_item(Item=user_data)
    print(f"Created new user record for {user.email}")
    
    return user_data


def sync_user_data(user, existing_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sync user data from JWT token to database if changed.
    Returns the updated user data.
    """
    updates_needed = False
    update_expression_parts = []
    expression_values = {}
    
    # Check for changes
    if user.email != existing_data.get('email'):
        update_expression_parts.append('email = :email')
        expression_values[':email'] = user.email
        updates_needed = True
    
    if user.given_name and user.given_name != existing_data.get('firstName'):
        update_expression_parts.append('firstName = :firstName')
        expression_values[':firstName'] = user.given_name
        updates_needed = True
    
    if user.family_name and user.family_name != existing_data.get('lastName'):
        update_expression_parts.append('lastName = :lastName')
        expression_values[':lastName'] = user.family_name
        updates_needed = True
    
    if user.role != existing_data.get('role'):
        update_expression_parts.append('#role = :role')
        expression_values[':role'] = user.role
        updates_needed = True
    
    if user.org_id and user.org_id != existing_data.get('orgId'):
        update_expression_parts.append('orgId = :orgId')
        expression_values[':orgId'] = user.org_id
        updates_needed = True
    
    if updates_needed:
        update_expression_parts.append('updatedAt = :updatedAt')
        expression_values[':updatedAt'] = datetime.now(timezone.utc).isoformat()
        
        update_kwargs = {
            'Key': {'userId': user.user_id},
            'UpdateExpression': 'SET ' + ', '.join(update_expression_parts),
            'ExpressionAttributeValues': expression_values,
            'ReturnValues': 'ALL_NEW'
        }
        
        # Handle reserved word 'role'
        if ':role' in expression_values:
            update_kwargs['ExpressionAttributeNames'] = {'#role': 'role'}
        
        response = users_table.update_item(**update_kwargs)
        print(f"Synced user data for {user.email}")
        return response['Attributes']
    
    return existing_data


def get_organization(org_id: str) -> Dict[str, Any]:
    """Fetch organization details."""
    try:
        response = organizations_table.get_item(Key={'orgId': org_id})
        if 'Item' in response:
            org = response['Item']
            # Return safe subset of org data
            return {
                'orgId': org.get('orgId'),
                'name': org.get('name'),
                'slug': org.get('slug'),
                'theme': org.get('theme'),
                'status': org.get('status')
            }
    except Exception as e:
        print(f"Error fetching organization {org_id}: {e}")
    return None


def get_user_permissions(user) -> Dict[str, bool]:
    """Get user's permission flags based on role."""
    return {
        'canManageOrganization': user.is_platform_admin or user.is_org_admin,
        'canManageUsers': user.is_platform_admin or user.is_org_admin,
        'canAssignTickets': user.is_agent,
        'canViewAllTickets': user.is_agent,
        'canCreateInternalNotes': user.is_agent,
        'canDeleteTickets': user.is_agent,
        'canHardDeleteTickets': user.is_platform_admin,
        'isPlatformAdmin': user.is_platform_admin,
        'isOrgAdmin': user.is_org_admin,
        'isTechnician': user.is_technician,
        'isCustomer': user.is_customer
    }


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