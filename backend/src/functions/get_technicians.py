"""
Lambda handler for listing technicians (for ticket assignment dropdown)
ENHANCED: Multi-tenant support - only returns technicians in user's organization
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
    Lambda handler for GET /users/technicians
    Returns list of technicians available for ticket assignment
    
    Multi-tenant behavior:
    - Platform admins: Can see all technicians (can filter by orgId query param)
    - Org admins/Technicians: See technicians in their organization only
    - Customers: Cannot access this endpoint
    
    Returns users with roles: platform_admin, org_admin, technician
    (Anyone who can be assigned tickets)
    """
    try:
        user = extract_user_from_event(event)
        
        # Only agents can view technician list
        if not user.is_agent:
            return create_response(403, {
                'error': 'You do not have permission to view technicians'
            })
        
        # Get query parameters
        params = event.get('queryStringParameters') or {}
        
        # Determine which org's technicians to fetch
        target_org_id = get_target_org_id(user, params)
        
        # Build filter for assignable roles
        assignable_roles = ['platform_admin', 'org_admin', 'technician', 'admin', 'agent']
        
        # Build filter expression
        filter_expression = build_filter_expression(target_org_id, assignable_roles)
        
        # Scan with filters
        response = users_table.scan(FilterExpression=filter_expression)
        technicians = response.get('Items', [])
        
        # Handle pagination
        while 'LastEvaluatedKey' in response:
            response = users_table.scan(
                FilterExpression=filter_expression,
                ExclusiveStartKey=response['LastEvaluatedKey']
            )
            technicians.extend(response.get('Items', []))
        
        # Format for dropdown display
        formatted_technicians = [format_technician(t) for t in technicians]
        
        # Sort by name
        formatted_technicians.sort(key=lambda x: x.get('name', ''))
        
        print(f"User {user.email} retrieved {len(formatted_technicians)} technicians (org: {target_org_id or 'all'})")
        
        return create_response(200, {
            'technicians': formatted_technicians,
            'count': len(formatted_technicians)
        })
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        print(f"DynamoDB error: {error_code} - {e}")
        return create_response(500, {'error': 'Failed to retrieve technicians'})
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return create_response(500, {'error': 'Internal server error'})


def get_target_org_id(user, params: Dict[str, str]) -> str:
    """
    Determine which organization's technicians to return.
    """
    if user.is_platform_admin:
        return params.get('orgId')  # None means all orgs
    
    return user.org_id


def build_filter_expression(target_org_id: str, assignable_roles: List[str]):
    """
    Build DynamoDB filter expression for technicians.
    """
    # Build role filter (any of the assignable roles)
    role_conditions = [Attr('role').eq(role) for role in assignable_roles]
    role_filter = role_conditions[0]
    for condition in role_conditions[1:]:
        role_filter = role_filter | condition
    
    # Add org filter if specified
    if target_org_id:
        return role_filter & Attr('orgId').eq(target_org_id)
    
    return role_filter


def format_technician(user_data: Dict[str, Any]) -> Dict[str, Any]:
    """Format user data for technician dropdown."""
    first_name = user_data.get('firstName', '')
    last_name = user_data.get('lastName', '')
    full_name = f"{first_name} {last_name}".strip()
    
    return {
        'userId': user_data.get('userId'),
        'email': user_data.get('email'),
        'name': full_name or user_data.get('email'),
        'firstName': first_name,
        'lastName': last_name,
        'role': user_data.get('role'),
        'orgId': user_data.get('orgId')
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