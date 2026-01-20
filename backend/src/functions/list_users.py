"""
Lambda handler for listing all users
Admin only - for user management
"""
import json
import os
from typing import Dict, Any
import boto3
from botocore.exceptions import ClientError

from auth import extract_user_from_event

# Initialize AWS resources
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
users_table = dynamodb.Table(os.environ.get('USERS_TABLE', 'dev-users'))
cognito = boto3.client('cognito-idp', region_name='us-east-1')
user_pool_id = os.environ.get('USER_POOL_ID', '')


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for GET /users
    Lists all users (Admin only)
    
    Query params:
        - role: Filter by role (CUSTOMER, TECH, ADMIN)
        - limit: Max number of users (default 50)
    """
    try:
        user = extract_user_from_event(event)
        
        # Verify admin role
        user_record = users_table.get_item(Key={'userId': user.user_id}).get('Item')
        if not user_record or user_record.get('role') != 'ADMIN':
            return create_response(403, {'error': 'Admin access required'})
        
        query_params = event.get('queryStringParameters') or {}
        role_filter = query_params.get('role', '').upper()
        limit = min(int(query_params.get('limit', 50)), 100)
        
        # Query users
        if role_filter and role_filter in ['CUSTOMER', 'TECH', 'ADMIN']:
            # Query by role using GSI
            response = users_table.query(
                IndexName='RoleIndex',
                KeyConditionExpression='#role = :role',
                ExpressionAttributeNames={'#role': 'role'},
                ExpressionAttributeValues={':role': role_filter},
                Limit=limit
            )
        else:
            # Scan all users
            response = users_table.scan(Limit=limit)
        
        users = response.get('Items', [])
        
        # Remove sensitive data
        for u in users:
            u.pop('passwordHash', None)  # Just in case
        
        return create_response(200, {
            'users': users,
            'count': len(users)
        })
        
    except ClientError as e:
        print(f"DynamoDB error: {e}")
        return create_response(500, {'error': 'Failed to list users'})
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