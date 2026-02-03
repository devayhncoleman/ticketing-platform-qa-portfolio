"""
Create Organization Lambda Function
- Only Platform Admin can create organizations
"""

import json
import boto3
import uuid
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

def is_slug_unique(slug):
    """Check if organization slug is unique"""
    response = organizations_table.scan(
        FilterExpression='slug = :slug',
        ExpressionAttributeValues={':slug': slug}
    )
    return len(response.get('Items', [])) == 0

def handler(event, context):
    """
    Create a new organization
    
    Only Platform Admin can create organizations
    """
    print("=== createOrganization Lambda started ===")
    
    # Get user claims
    claims = get_user_claims(event)
    
    if not claims or not claims.get('userId'):
        print("Returning 401 - No valid claims")
        return json_response(401, {'error': 'Unauthorized'})
    
    # Only platform admin can create organizations
    if not is_platform_admin(claims):
        print("Returning 403 - Not platform admin")
        return json_response(403, {'error': 'Only platform administrators can create organizations'})
    
    try:
        # Parse request body
        body = json.loads(event.get('body', '{}'))
        
        name = body.get('name', '').strip()
        slug = body.get('slug', '').strip().lower()
        
        # Validate required fields
        if not name:
            return json_response(400, {'error': 'Organization name is required'})
        
        if not slug:
            return json_response(400, {'error': 'Organization slug is required'})
        
        # Validate slug format (alphanumeric and hyphens only)
        if not all(c.isalnum() or c == '-' for c in slug):
            return json_response(400, {'error': 'Slug must contain only letters, numbers, and hyphens'})
        
        # Check if slug is unique
        if not is_slug_unique(slug):
            print(f"Slug '{slug}' already exists")
            return json_response(409, {'error': f"Organization with slug '{slug}' already exists"})
        
        # Create organization
        org_id = f"org_{uuid.uuid4().hex[:12]}"
        timestamp = datetime.now(timezone.utc).isoformat()
        
        organization = {
            'orgId': org_id,
            'name': name,
            'slug': slug,
            'status': 'active',
            'createdAt': timestamp,
            'updatedAt': timestamp,
            'createdBy': claims['userId']
        }
        
        # Add optional theme if provided
        if 'theme' in body:
            organization['theme'] = body['theme']
        
        # Save to DynamoDB
        organizations_table.put_item(Item=organization)
        
        print(f"Created organization: {org_id}")
        return json_response(201, organization)
    
    except json.JSONDecodeError:
        return json_response(400, {'error': 'Invalid JSON in request body'})
    except Exception as e:
        print(f"Error: {str(e)}")
        return json_response(500, {'error': f'Failed to create organization: {str(e)}'})