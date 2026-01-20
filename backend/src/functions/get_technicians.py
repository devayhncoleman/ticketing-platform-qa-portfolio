"""
Lambda handler for listing technicians
Used in Admin console for ticket assignment dropdown
Returns only users with TECH or ADMIN role
"""
import json
import os
from typing import Dict, Any
import boto3
from botocore.exceptions import ClientError

from auth import extract_user_from_event

# Initialize DynamoDB
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
users_table = dynamodb.Table(os.environ.get('USERS_TABLE', 'dev-users'))


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for GET /technicians
    Lists all users with TECH or ADMIN role (for assignment dropdown)
    
    Returns simplified user objects with just id, name, email
    """
    try:
        user = extract_user_from_event(event)
        
        # Get user's role - must be at least TECH to see technician list
        user_record = users_table.get_item(Key={'userId': user.user_id}).get('Item')
        user_role = user_record.get('role', 'CUSTOMER') if user_record else 'CUSTOMER'
        
        if user_role not in ['TECH', 'ADMIN']:
            return create_response(403, {'error': 'Access denied'})
        
        # Query technicians using RoleIndex
        techs = []
        
        # Get TECHs
        tech_response = users_table.query(
            IndexName='RoleIndex',
            KeyConditionExpression='#role = :role',
            ExpressionAttributeNames={'#role': 'role'},
            ExpressionAttributeValues={':role': 'TECH'}
        )
        techs.extend(tech_response.get('Items', []))
        
        # Get ADMINs (they can also be assigned tickets)
        admin_response = users_table.query(
            IndexName='RoleIndex',
            KeyConditionExpression='#role = :role',
            ExpressionAttributeNames={'#role': 'role'},
            ExpressionAttributeValues={':role': 'ADMIN'}
        )
        techs.extend(admin_response.get('Items', []))
        
        # Simplify response (only needed fields for dropdown)
        simplified_techs = [
            {
                'userId': t.get('userId'),
                'name': f"{t.get('firstName', '')} {t.get('lastName', '')}".strip() or t.get('email', 'Unknown'),
                'email': t.get('email'),
                'role': t.get('role')
            }
            for t in techs
        ]
        
        # Sort by name
        simplified_techs.sort(key=lambda x: x['name'].lower())
        
        return create_response(200, {
            'technicians': simplified_techs,
            'count': len(simplified_techs)
        })
        
    except ClientError as e:
        print(f"DynamoDB error: {e}")
        return create_response(500, {'error': 'Failed to list technicians'})
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