"""
Lambda handler for listing users
ENHANCED: Multi-tenant support - filters users by organization
"""
import json
import os
from typing import Dict, Any, List
import boto3
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Attr

from auth import extract_user_from_event

# Initialize DynamoDB
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
users_table = dynamodb.Table(os.environ.get('USERS_TABLE', 'dev-users'))


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for GET /users
    Lists users based on role and organization membership
    
    Multi-tenant behavior:
    - Platform admins: Can see all users (can filter by orgId query param)
    - Org admins: Can see all users in their organization
    - Technicians: Can see users in their organization
    - Customers: Can only see themselves
    
    Query parameters:
    - role: Filter by role (platform_admin, org_admin, technician, customer)
    - orgId: Filter by organization (platform_admin only)
    - limit: Max items to return (default 100)
    """
    try:
        user = extract_user_from_event(event)
        
        # Customers can only see themselves
        if user.is_customer:
            return create_response(200, {
                'users': [get_user_safe_data(user)],
                'count': 1
            })
        
        # Get query parameters
        params = event.get('queryStringParameters') or {}
        
        # Determine which org's users to fetch
        target_org_id = get_target_org_id(user, params)
        
        # Build filter expression
        filter_expression = build_filter_expression(user, params, target_org_id)
        
        # Scan with filters
        scan_kwargs = {}
        if filter_expression:
            scan_kwargs['FilterExpression'] = filter_expression
        
        response = users_table.scan(**scan_kwargs)
        users = response.get('Items', [])
        
        # Handle pagination
        while 'LastEvaluatedKey' in response:
            scan_kwargs['ExclusiveStartKey'] = response['LastEvaluatedKey']
            response = users_table.scan(**scan_kwargs)
            users.extend(response.get('Items', []))
        
        # Remove sensitive data
        safe_users = [sanitize_user_data(u) for u in users]
        
        # Sort by email
        safe_users.sort(key=lambda x: x.get('email', ''))
        
        # Apply limit
        limit = int(params.get('limit', 100))
        safe_users = safe_users[:limit]
        
        print(f"User {user.email} retrieved {len(safe_users)} users (org: {target_org_id or 'all'})")
        
        return create_response(200, {
            'users': safe_users,
            'count': len(safe_users)
        })
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        print(f"DynamoDB error: {error_code} - {e}")
        return create_response(500, {'error': 'Failed to retrieve users'})
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return create_response(500, {'error': 'Internal server error'})


def get_target_org_id(user, params: Dict[str, str]) -> str:
    """
    Determine which organization's users to return.
    
    - Platform admins can specify orgId param or see all
    - Others are limited to their own org
    """
    if user.is_platform_admin:
        return params.get('orgId')  # None means all orgs
    
    return user.org_id


def build_filter_expression(user, params: Dict[str, str], target_org_id: str):
    """
    Build DynamoDB filter expression based on user role and query params.
    """
    conditions = []
    
    # Multi-tenant filtering by orgId
    if target_org_id:
        conditions.append(Attr('orgId').eq(target_org_id))
    
    # Role filter
    if params.get('role'):
        conditions.append(Attr('role').eq(params['role'].lower()))
    
    # Combine conditions with AND
    if not conditions:
        return None
    
    filter_expression = conditions[0]
    for condition in conditions[1:]:
        filter_expression = filter_expression & condition
    
    return filter_expression


def sanitize_user_data(user_data: Dict[str, Any]) -> Dict[str, Any]:
    """Remove sensitive fields from user data."""
    safe_fields = [
        'userId', 'email', 'firstName', 'lastName', 'role', 
        'orgId', 'createdAt', 'updatedAt'
    ]
    return {k: v for k, v in user_data.items() if k in safe_fields}


def get_user_safe_data(user) -> Dict[str, Any]:
    """Convert UserContext to safe dictionary for API response."""
    return {
        'userId': user.user_id,
        'email': user.email,
        'firstName': user.given_name or '',
        'lastName': user.family_name or '',
        'role': user.role,
        'orgId': user.org_id
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