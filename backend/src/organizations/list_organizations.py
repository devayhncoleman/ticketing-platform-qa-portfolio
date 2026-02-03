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
    """Extract user claims from JWT token via API Gateway"""
    try:
        # Debug: Print the entire event to CloudWatch
        print(f"Full event: {json.dumps(event, default=str)}")
        
        # API Gateway with Cognito Authorizer puts claims here
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
        print("is_platform_admin: No claims provided")
        return False
    
    role = claims.get('role', '')
    print(f"is_platform_admin check - role: '{role}'")
    
    result = role == 'platform_admin'
    print(f"is_platform_admin result: {result}")
    return result

def handler(event, context):
    """
    List organizations
    
    Platform Admin: Returns all organizations
    Other users: Returns only their organization
    """
    print("=== listOrganizations Lambda started ===")
    
    # Get user claims
    claims = get_user_claims(event)
    
    if not claims:
        print("Returning 401 - No valid claims")
        return json_response(401, {'error': 'Unauthorized'})
    
    # Check if user has any identifying info
    if not claims.get('userId'):
        print("Returning 401 - No userId in claims")
        return json_response(401, {'error': 'Unauthorized'})
    
    try:
        if is_platform_admin(claims):
            print("User is platform_admin - fetching all orgs")
            # Platform admin sees all organizations
            response = organizations_table.scan()
            organizations = response.get('Items', [])
            
            # Handle pagination if needed
            while 'LastEvaluatedKey' in response:
                response = organizations_table.scan(
                    ExclusiveStartKey=response['LastEvaluatedKey']
                )
                organizations.extend(response.get('Items', []))
            
            print(f"Returning {len(organizations)} organizations")
            return json_response(200, {
                'organizations': organizations,
                'count': len(organizations)
            })
        else:
            print("User is NOT platform_admin - fetching their org only")
            # Regular users only see their own organization
            org_id = claims.get('orgId')
            
            if not org_id:
                print("User has no orgId - returning empty list")
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
        print(f"Error: {str(e)}")
        return json_response(500, {
            'error': f'Failed to list organizations: {str(e)}'
        })