"""
Update Organization Lambda Function
- Org Admins can update their own organization
- Platform Admins can update any organization
"""

import json
import boto3
from datetime import datetime
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

def is_org_admin(claims):
    """Check if user is org admin"""
    return claims and claims.get('role') == 'org_admin'

def can_update_org(claims, org_id):
    """Check if user can update the specified organization"""
    if is_platform_admin(claims):
        return True  # Platform admin can update any org
    if is_org_admin(claims) and claims.get('orgId') == org_id:
        return True  # Org admin can update their own org
    return False

def handler(event, context):
    """
    Update an organization
    
    Allowed fields: name, theme, status (platform admin only)
    Org admins can update: name, theme
    Platform admins can update: name, theme, status
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
    if not can_update_org(claims, org_id):
        return json_response(403, {
            'error': 'Forbidden: You do not have permission to update this organization'
        })
    
    # Parse request body
    try:
        body = json.loads(event.get('body', '{}'))
    except json.JSONDecodeError:
        return json_response(400, {'error': 'Invalid JSON in request body'})
    
    if not body:
        return json_response(400, {'error': 'Request body cannot be empty'})
    
    # Build update expression
    update_expression_parts = []
    expression_attribute_names = {}
    expression_attribute_values = {}
    
    # Allowed fields for org admins
    allowed_fields = ['name', 'theme']
    
    # Platform admins can also update status
    if is_platform_admin(claims):
        allowed_fields.extend(['status'])
    
    for field in allowed_fields:
        if field in body:
            placeholder = f'#{field}'
            value_placeholder = f':{field}'
            update_expression_parts.append(f'{placeholder} = {value_placeholder}')
            expression_attribute_names[placeholder] = field
            expression_attribute_values[value_placeholder] = body[field]
    
    if not update_expression_parts:
        return json_response(400, {
            'error': 'No valid fields to update'
        })
    
    # Add updatedAt timestamp
    update_expression_parts.append('#updatedAt = :updatedAt')
    expression_attribute_names['#updatedAt'] = 'updatedAt'
    expression_attribute_values[':updatedAt'] = datetime.utcnow().isoformat() + 'Z'
    
    update_expression = 'SET ' + ', '.join(update_expression_parts)
    
    # Update in DynamoDB
    try:
        response = organizations_table.update_item(
            Key={'orgId': org_id},
            UpdateExpression=update_expression,
            ExpressionAttributeNames=expression_attribute_names,
            ExpressionAttributeValues=expression_attribute_values,
            ReturnValues='ALL_NEW'
        )
        
        return json_response(200, response.get('Attributes', {}))
    
    except Exception as e:
        return json_response(500, {
            'error': f'Failed to update organization: {str(e)}'
        })