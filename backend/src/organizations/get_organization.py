"""
Get Organization Lambda Function
Retrieve a single organization by ID
"""

import json
import boto3
from decimal import Decimal

dynamodb = boto3.resource('dynamodb')
organizations_table = dynamodb.Table('Organizations')

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return int(obj) if obj % 1 == 0 else float(obj)
        return super(DecimalEncoder, self).default(obj)

def json_response(status_code, body):
    """Standard API response format"""
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,Authorization',
            'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS'
        },
        'body': json.dumps(body, cls=DecimalEncoder)
    }

def get_user_claims(event):
    """Extract user claims from JWT token"""
    try:
        claims = event['requestContext']['authorizer']['claims']
        return {
            'userId': claims.get('sub'),
            'role': claims.get('custom:role', 'customer'),
            'orgId': claims.get('custom:orgId'),
            'email': claims.get('email')
        }
    except (KeyError, TypeError):
        return None

def is_platform_admin(claims):
    """Check if user is platform admin"""
    return claims and claims.get('role') == 'platform_admin'

def user_belongs_to_org(claims, org_id):
    """Check if user belongs to the specified organization"""
    if is_platform_admin(claims):
        return True  # Platform admin can access any org
    return claims and claims.get('orgId') == org_id

def handler(event, context):
    """
    Get a single organization by ID
    
    Users can only view their own organization
    Platform admins can view any organization
    """
    claims = get_user_claims(event)
    
    if not claims:
        return json_response(401, {'error': 'Unauthorized'})
    
    # Get orgId from path parameters
    try:
        org_id = event['pathParameters']['orgId']
    except (KeyError, TypeError):
        return json_response(400, {'error': 'Missing orgId in path'})
    
    # Check authorization
    if not user_belongs_to_org(claims, org_id):
        return json_response(403, {
            'error': 'Forbidden: You do not have access to this organization'
        })
    
    # Fetch organization
    try:
        response = organizations_table.get_item(
            Key={'orgId': org_id}
        )
        
        org = response.get('Item')
        
        if not org:
            return json_response(404, {
                'error': f'Organization {org_id} not found'
            })
        
        return json_response(200, org)
    
    except Exception as e:
        return json_response(500, {
            'error': f'Failed to get organization: {str(e)}'
        })