"""
List Organizations Lambda Function
- Platform Admin: See all organizations
- Org Admin/Users: See only their organization
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

def handler(event, context):
    """
    List organizations
    
    Platform Admin: Returns all organizations
    Other users: Returns only their organization
    """
    claims = get_user_claims(event)
    
    if not claims:
        return json_response(401, {'error': 'Unauthorized'})
    
    try:
        if is_platform_admin(claims):
            # Platform admin sees all organizations
            response = organizations_table.scan()
            organizations = response.get('Items', [])
            
            # Handle pagination if needed
            while 'LastEvaluatedKey' in response:
                response = organizations_table.scan(
                    ExclusiveStartKey=response['LastEvaluatedKey']
                )
                organizations.extend(response.get('Items', []))
            
            return json_response(200, {
                'organizations': organizations,
                'count': len(organizations)
            })
        else:
            # Regular users only see their own organization
            org_id = claims.get('orgId')
            
            if not org_id:
                return json_response(200, {
                    'organizations': [],
                    'count': 0
                })
            
            response = organizations_table.get_item(
                Key={'orgId': org_id}
            )
            
            org = response.get('Item')
            
            if org:
                return json_response(200, {
                    'organizations': [org],
                    'count': 1
                })
            else:
                return json_response(200, {
                    'organizations': [],
                    'count': 0
                })
    
    except Exception as e:
        return json_response(500, {
            'error': f'Failed to list organizations: {str(e)}'
        })