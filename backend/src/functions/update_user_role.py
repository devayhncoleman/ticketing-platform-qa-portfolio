"""
Lambda handler for updating user roles
Admin only - promotes users to TECH or ADMIN, or demotes
"""
import json
import os
from datetime import datetime, timezone
from typing import Dict, Any
import boto3
from botocore.exceptions import ClientError

from auth import extract_user_from_event

# Initialize AWS resources
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
users_table = dynamodb.Table(os.environ.get('USERS_TABLE', 'dev-users'))
cognito = boto3.client('cognito-idp', region_name='us-east-1')
user_pool_id = os.environ.get('USER_POOL_ID', '')

VALID_ROLES = ['CUSTOMER', 'TECH', 'ADMIN']


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for PATCH /users/{userId}/role
    Updates a user's role (Admin only)
    
    Request body:
        - role: New role (CUSTOMER, TECH, ADMIN)
    """
    try:
        user = extract_user_from_event(event)
        
        # Verify admin role
        admin_record = users_table.get_item(Key={'userId': user.user_id}).get('Item')
        if not admin_record or admin_record.get('role') != 'ADMIN':
            return create_response(403, {'error': 'Admin access required'})
        
        # Get target user ID
        target_user_id = event.get('pathParameters', {}).get('userId')
        if not target_user_id:
            return create_response(400, {'error': 'User ID is required'})
        
        # Prevent self-demotion
        if target_user_id == user.user_id:
            return create_response(400, {'error': 'Cannot change your own role'})
        
        # Parse request body
        body = json.loads(event.get('body', '{}'))
        new_role = body.get('role', '').upper()
        
        if new_role not in VALID_ROLES:
            return create_response(400, {
                'error': f'Invalid role. Must be one of: {", ".join(VALID_ROLES)}'
            })
        
        # Check target user exists
        target_user = users_table.get_item(Key={'userId': target_user_id}).get('Item')
        if not target_user:
            return create_response(404, {'error': 'User not found'})
        
        now = datetime.now(timezone.utc).isoformat()
        
        # Update in DynamoDB
        users_table.update_item(
            Key={'userId': target_user_id},
            UpdateExpression='SET #role = :role, updatedAt = :now, updatedBy = :admin',
            ExpressionAttributeNames={'#role': 'role'},
            ExpressionAttributeValues={
                ':role': new_role,
                ':now': now,
                ':admin': user.user_id
            }
        )
        
        # Also update Cognito custom attribute
        try:
            cognito.admin_update_user_attributes(
                UserPoolId=user_pool_id,
                Username=target_user.get('email', target_user_id),
                UserAttributes=[
                    {'Name': 'custom:role', 'Value': new_role}
                ]
            )
        except Exception as e:
            print(f"Warning: Could not update Cognito attribute: {e}")
            # Continue anyway - DynamoDB is source of truth
        
        print(f"User {target_user_id} role changed to {new_role} by admin {user.email}")
        
        return create_response(200, {
            'userId': target_user_id,
            'role': new_role,
            'updatedAt': now,
            'message': f'User role updated to {new_role}'
        })
        
    except json.JSONDecodeError:
        return create_response(400, {'error': 'Invalid JSON in request body'})
    except ClientError as e:
        print(f"AWS error: {e}")
        return create_response(500, {'error': 'Failed to update user role'})
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return create_response(500, {'error': 'Internal server error'})


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