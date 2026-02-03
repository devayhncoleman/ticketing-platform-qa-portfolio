"""
Update Organization Lambda Function
- Platform Admin: Can update any organization (including status)
- Org Admin: Can update their own organization (name, theme only)
"""

import json
import boto3
from datetime import datetime, timezone
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

def is_org_admin(claims):
    """Check if user is org admin"""
    if not claims:
        return False
    role = claims.get('role', '')
    return role == 'org_admin'

def handler(event, context):
    """
    Update an organization
    
    Platform Admin: Can update any organization (all fields including status)
    Org Admin: Can update their own organization (name, theme only)
    """
    print("=== updateOrganization Lambda started ===")
    
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
        
        print(f"Updating org_id: {org_id}")
        
        # Parse request body
        body = json.loads(event.get('body', '{}'))
        
        # Check authorization
        is_admin = is_platform_admin(claims)
        user_org_id = claims.get('orgId', '')
        
        if not is_admin:
            # Non-platform-admins can only update their own org
            if not is_org_admin(claims):
                return json_response(403, {'error': 'Only org admins can update organizations'})
            
            if user_org_id != org_id:
                return json_response(403, {'error': 'You can only update your own organization'})
        
        # Build update expression
        update_parts = []
        expression_values = {}
        expression_names = {}
        
        # Fields that org admins can update
        if 'name' in body:
            update_parts.append('#n = :name')
            expression_values[':name'] = body['name']
            expression_names['#n'] = 'name'
        
        if 'theme' in body:
            update_parts.append('theme = :theme')
            expression_values[':theme'] = body['theme']
        
        # Fields that only platform admin can update
        if is_admin:
            if 'status' in body:
                valid_statuses = ['active', 'suspended', 'trial']
                if body['status'] not in valid_statuses:
                    return json_response(400, {'error': f"Status must be one of: {', '.join(valid_statuses)}"})
                update_parts.append('#s = :status')
                expression_values[':status'] = body['status']
                expression_names['#s'] = 'status'
        
        if not update_parts:
            return json_response(400, {'error': 'No valid fields to update'})
        
        # Add updatedAt timestamp
        update_parts.append('updatedAt = :updatedAt')
        expression_values[':updatedAt'] = datetime.now(timezone.utc).isoformat()
        
        # Build the update expression
        update_expression = 'SET ' + ', '.join(update_parts)
        
        # Execute update
        update_params = {
            'Key': {'orgId': org_id},
            'UpdateExpression': update_expression,
            'ExpressionAttributeValues': expression_values,
            'ReturnValues': 'ALL_NEW'
        }
        
        if expression_names:
            update_params['ExpressionAttributeNames'] = expression_names
        
        response = organizations_table.update_item(**update_params)
        
        updated_org = response.get('Attributes', {})
        
        print(f"Updated organization: {org_id}")
        return json_response(200, updated_org)
    
    except json.JSONDecodeError:
        return json_response(400, {'error': 'Invalid JSON in request body'})
    except Exception as e:
        print(f"Error: {str(e)}")
        return json_response(500, {'error': f'Failed to update organization: {str(e)}'})