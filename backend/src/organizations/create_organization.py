"""
Create Organization Lambda Function
Only Platform Admins can create new organizations
"""

import json
import boto3
import uuid
from datetime import datetime

dynamodb = boto3.resource('dynamodb')
organizations_table = dynamodb.Table('Organizations')

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
        'body': json.dumps(body)
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

def slug_exists(slug):
    """Check if organization slug already exists"""
    try:
        # Use GSI or scan to check for existing slug
        response = organizations_table.scan(
            FilterExpression='slug = :slug',
            ExpressionAttributeValues={':slug': slug}
        )
        return len(response.get('Items', [])) > 0
    except Exception:
        return False

def handler(event, context):
    """
    Create a new organization
    
    Required: Platform Admin role
    Body: { name: string, slug: string, theme?: object }
    """
    # Check authorization
    claims = get_user_claims(event)
    
    if not is_platform_admin(claims):
        return json_response(403, {
            'error': 'Forbidden: Only platform administrators can create organizations'
        })
    
    # Parse request body
    try:
        body = json.loads(event.get('body', '{}'))
    except json.JSONDecodeError:
        return json_response(400, {'error': 'Invalid JSON in request body'})
    
    # Validate required fields
    name = body.get('name')
    slug = body.get('slug')
    
    if not name or not slug:
        return json_response(400, {
            'error': 'Missing required fields: name and slug are required'
        })
    
    # Validate slug format (lowercase, alphanumeric, hyphens only)
    slug = slug.lower().strip()
    if not slug.replace('-', '').isalnum():
        return json_response(400, {
            'error': 'Invalid slug format: use only lowercase letters, numbers, and hyphens'
        })
    
    # Check if slug already exists
    if slug_exists(slug):
        return json_response(409, {
            'error': f'Organization with slug "{slug}" already exists'
        })
    
    # Create organization
    org_id = f'org_{uuid.uuid4().hex[:12]}'
    timestamp = datetime.utcnow().isoformat() + 'Z'
    
    organization = {
        'orgId': org_id,
        'name': name.strip(),
        'slug': slug,
        'status': 'active',
        'createdAt': timestamp,
        'updatedAt': timestamp,
        'createdBy': claims.get('userId')
    }
    
    # Add optional theme if provided
    if 'theme' in body:
        organization['theme'] = body['theme']
    
    # Save to DynamoDB
    try:
        organizations_table.put_item(Item=organization)
    except Exception as e:
        return json_response(500, {
            'error': f'Failed to create organization: {str(e)}'
        })
    
    return json_response(201, organization)