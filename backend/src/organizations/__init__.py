"""
Organizations Management Lambda Functions
Multi-Tenant SaaS Architecture

Roles:
- platform_admin: Can manage all organizations (YOU)
- org_admin: Can manage their own organization
- technician: Can view their org info
- customer: Can view their org info
"""

import json
import boto3
import uuid
from datetime import datetime
from decimal import Decimal

# Initialize DynamoDB
dynamodb = boto3.resource('dynamodb')
organizations_table = dynamodb.Table('Organizations')

# Helper to convert Decimal to int/float for JSON serialization
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

def user_belongs_to_org(claims, org_id):
    """Check if user belongs to the specified organization"""
    if is_platform_admin(claims):
        return True  # Platform admin can access any org
    return claims and claims.get('orgId') == org_id