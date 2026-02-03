"""
Lambda handler for updating user roles
ENHANCED: Multi-tenant support - verifies org access before role changes
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


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for PUT /users/{userId}/role
    Updates a user's role
    
    Multi-tenant behavior:
    - Platform admins: Can change any user's role to any value
    - Org admins: Can change roles within their org (except to platform_admin)
    - Technicians/Customers: Cannot change roles
    
    Request body:
    - role: New role (platform_admin, org_admin, technician, customer)
    - orgId: Organization to assign user to (platform_admin only)
    """
    try:
        user = extract_user_from_event(event)
        
        # Only admins can update roles
        if not user.is_admin:
            return create_response(403, {
                'error': 'Only administrators can update user roles'
            })
        
        # Get target user ID from path parameters
        path_params = event.get('pathParameters') or {}
        target_user_id = path_params.get('userId')
        
        if not target_user_id:
            return create_response(400, {'error': 'User ID is required'})
        
        # Fetch target user
        response = users_table.get_item(Key={'userId': target_user_id})
        
        if 'Item' not in response:
            return create_response(404, {'error': 'User not found'})
        
        target_user = response['Item']
        
        # Parse request body
        body = json.loads(event.get('body', '{}'))
        new_role = body.get('role', '').lower()
        new_org_id = body.get('orgId')
        
        # Validate new role
        valid_roles = ['platform_admin', 'org_admin', 'technician', 'customer']
        if new_role and new_role not in valid_roles:
            return create_response(400, {
                'error': f'Invalid role. Must be one of: {", ".join(valid_roles)}'
            })
        
        # Authorization checks based on who's making the change
        target_org_id = target_user.get('orgId')
        
        if not user.is_platform_admin:
            # Org admins can only manage users in their own org
            if target_org_id != user.org_id:
                return create_response(403, {
                    'error': 'You can only manage users in your organization'
                })
            
            # Org admins cannot promote to platform_admin
            if new_role == 'platform_admin':
                return create_response(403, {
                    'error': 'Only platform administrators can grant platform admin access'
                })
            
            # Org admins cannot change other org admins' roles
            if target_user.get('role', '').lower() == 'org_admin' and target_user_id != user.user_id:
                return create_response(403, {
                    'error': 'You cannot change another organization admin\'s role'
                })
            
            # Org admins cannot assign users to different orgs
            if new_org_id and new_org_id != user.org_id:
                return create_response(403, {
                    'error': 'You can only assign users to your own organization'
                })
        
        # Prevent removing the last platform admin (safety check)
        if target_user.get('role', '').lower() == 'platform_admin' and new_role != 'platform_admin':
            platform_admin_count = count_platform_admins()
            if platform_admin_count <= 1:
                return create_response(400, {
                    'error': 'Cannot remove the last platform administrator'
                })
        
        # Build update expression
        update_parts = []
        expression_values = {}
        expression_names = {}
        
        if new_role:
            update_parts.append('#role = :role')
            expression_values[':role'] = new_role
            expression_names['#role'] = 'role'
        
        if new_org_id is not None:  # Allow setting to None to remove from org
            update_parts.append('orgId = :orgId')
            expression_values[':orgId'] = new_org_id if new_org_id else None
        
        if not update_parts:
            return create_response(400, {'error': 'No valid fields to update'})
        
        # Add metadata
        now = datetime.now(timezone.utc).isoformat()
        update_parts.append('updatedAt = :updatedAt')
        update_parts.append('updatedBy = :updatedBy')
        expression_values[':updatedAt'] = now
        expression_values[':updatedBy'] = user.user_id
        
        # Execute update
        update_kwargs = {
            'Key': {'userId': target_user_id},
            'UpdateExpression': 'SET ' + ', '.join(update_parts),
            'ExpressionAttributeValues': expression_values,
            'ReturnValues': 'ALL_NEW'
        }
        
        if expression_names:
            update_kwargs['ExpressionAttributeNames'] = expression_names
        
        response = users_table.update_item(**update_kwargs)
        updated_user = response['Attributes']
        
        # Remove sensitive data from response
        safe_user = sanitize_user_data(updated_user)
        
        print(f"User {user.email} updated role for {target_user.get('email')} to {new_role}")
        return create_response(200, safe_user)
        
    except json.JSONDecodeError:
        return create_response(400, {'error': 'Invalid JSON in request body'})
    except ClientError as e:
        error_code = e.response['Error']['Code']
        print(f"DynamoDB error: {error_code} - {e}")
        return create_response(500, {'error': 'Failed to update user role'})
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return create_response(500, {'error': 'Internal server error'})


def count_platform_admins() -> int:
    """Count the number of platform admins in the system."""
    try:
        from boto3.dynamodb.conditions import Attr
        response = users_table.scan(
            FilterExpression=Attr('role').eq('platform_admin'),
            Select='COUNT'
        )
        return response.get('Count', 0)
    except Exception as e:
        print(f"Error counting platform admins: {e}")
        return 999  # Return high number to prevent accidental removal


def sanitize_user_data(user_data: Dict[str, Any]) -> Dict[str, Any]:
    """Remove sensitive fields from user data."""
    safe_fields = [
        'userId', 'email', 'firstName', 'lastName', 'role',
        'orgId', 'createdAt', 'updatedAt', 'updatedBy'
    ]
    return {k: v for k, v in user_data.items() if k in safe_fields}


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