"""
Get Organization Lambda Function
- Platform Admin: Can view any organization
- Org Users: Can only view their own organization
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
    """Extract user claims from JWT token via API Gateway"""
    try:
        print(f"Full event: {json.dumps(event, default=str)}")
        
        claims = event.get('requestContext', {}).get('authorizer', {}).get('claims', {})
        
        print(f"Extracted claims: {json.dumps(claims, default=str)}")
        
        if not claims:
            print("No claims found in event")
            return None
        
        user_claims = {
            'userId': claims.get('sub', ''),
            'role': claims.get('custom:role', ''),
            'orgId': claims.get('custom:orgId', ''),
            'email': claims.get('email', '')
        }
        
        print(f"User claims: {json.dumps(user_claims)}")
        return user_claims
        
    except Exception as e:
        print(f"Error extracting claims: {str(e)}")
        return None

def is_platform_admin(claims):
    """Check if user is platform admin"""
    if not claims:
        return False
    role = claims.get('role', '')
    print(f"is_platform_admin check - role: '{role}'")
    return role == 'platform_admin'

def handler(event, context):
    """
    Get a single organization by ID
    
    Platform Admin: Can view any organization
    Other users: Can only view their own organization
    """
    print("=== getOrganization Lambda started ===")
    
    # Get user claims
    claims = get_user_claims(event)
    
    if not claims or not claims.get('userId'):
        print("Returning 401 - No valid claims")
        return json_response(401, {'error': 'Unauthorized'})
    
    try:
        # Get orgId from path parameters
        org_id = event.get('pathParameters', {}).get('orgId')
        
        if not org_id:
            return json_response(400, {'error': 'Organization ID is required'})
        
        print(f"Requested org_id: {org_id}")
        
        # Check authorization
        if not is_platform_admin(claims):
            # Non-admin users can only view their own org
            user_org_id = claims.get('orgId', '')
            if user_org_id != org_id:
                print(f"User org '{user_org_id}' doesn't match requested org '{org_id}'")
                return json_response(403, {'error': 'You can only view your own organization'})
        
        # Get organization from DynamoDB
        response = organizations_table.get_item(
            Key={'orgId': org_id}
        )
        
        organization = response.get('Item')
        
        if not organization:
            return json_response(404, {'error': 'Organization not found'})
        
        print(f"Returning organization: {org_id}")
        return json_response(200, organization)
    
    except Exception as e:
        print(f"Error: {str(e)}")
        return json_response(500, {'error': f'Failed to get organization: {str(e)}'})