"""
Lambda handler for listing tickets
ENHANCED: Multi-tenant support - filters tickets by organization
"""
import json
import os
from typing import Dict, Any, List
import boto3
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key, Attr

from auth import extract_user_from_event

# Initialize DynamoDB
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
tickets_table = dynamodb.Table(os.environ.get('TICKETS_TABLE', 'dev-tickets'))


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for GET /tickets
    Lists tickets based on user role and organization membership
    
    Multi-tenant behavior:
    - Platform admins: See all tickets (can filter by orgId query param)
    - Org admins/Technicians: See all tickets in their organization
    - Customers: See only their own tickets
    
    Query parameters:
    - status: Filter by status (OPEN, IN_PROGRESS, RESOLVED, CLOSED)
    - priority: Filter by priority (LOW, MEDIUM, HIGH, CRITICAL)
    - assignedTo: Filter by assigned technician
    - orgId: Filter by organization (platform_admin only)
    - limit: Max items to return (default 50)
    """
    try:
        user = extract_user_from_event(event)
        
        # Get query parameters
        params = event.get('queryStringParameters') or {}
        
        # Determine which org's tickets to fetch
        target_org_id = get_target_org_id(user, params)
        
        # Build filter expression based on user role and org
        filter_expression, expression_values = build_filter_expression(user, params, target_org_id)
        
        # Scan with filters (Note: For production, consider using GSI on orgId)
        scan_kwargs = {}
        if filter_expression:
            scan_kwargs['FilterExpression'] = filter_expression
        if expression_values:
            scan_kwargs['ExpressionAttributeValues'] = expression_values
        
        # Execute scan
        response = tickets_table.scan(**scan_kwargs)
        tickets = response.get('Items', [])
        
        # Handle pagination if there's more data
        while 'LastEvaluatedKey' in response:
            scan_kwargs['ExclusiveStartKey'] = response['LastEvaluatedKey']
            response = tickets_table.scan(**scan_kwargs)
            tickets.extend(response.get('Items', []))
        
        # Sort by createdAt descending (newest first)
        tickets.sort(key=lambda x: x.get('createdAt', ''), reverse=True)
        
        # Apply limit
        limit = int(params.get('limit', 50))
        tickets = tickets[:limit]
        
        print(f"User {user.email} retrieved {len(tickets)} tickets (org: {target_org_id or 'all'})")
        
        return create_response(200, {
            'tickets': tickets,
            'count': len(tickets)
        })
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        print(f"DynamoDB error: {error_code} - {e}")
        return create_response(500, {'error': 'Failed to retrieve tickets'})
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return create_response(500, {'error': 'Internal server error'})


def get_target_org_id(user, params: Dict[str, str]) -> str:
    """
    Determine which organization's tickets to return.
    
    - Platform admins can specify orgId param or see all
    - Others are limited to their own org
    """
    # Platform admins can filter by any org or see all
    if user.is_platform_admin:
        return params.get('orgId')  # None means all orgs
    
    # Everyone else is limited to their own org
    return user.org_id


def build_filter_expression(user, params: Dict[str, str], target_org_id: str):
    """
    Build DynamoDB filter expression based on user role and query params.
    
    Returns:
        Tuple of (filter_expression, expression_attribute_values)
    """
    conditions = []
    expression_values = {}
    
    # Multi-tenant filtering by orgId
    if target_org_id:
        conditions.append(Attr('orgId').eq(target_org_id))
    
    # Customer-specific filtering: only see own tickets
    if user.is_customer:
        conditions.append(Attr('createdBy').eq(user.user_id))
    
    # Status filter
    if params.get('status'):
        conditions.append(Attr('status').eq(params['status'].upper()))
    
    # Priority filter
    if params.get('priority'):
        conditions.append(Attr('priority').eq(params['priority'].upper()))
    
    # Assigned to filter
    if params.get('assignedTo'):
        conditions.append(Attr('assignedTo').eq(params['assignedTo']))
    
    # Category filter
    if params.get('category'):
        conditions.append(Attr('category').eq(params['category']))
    
    # Combine conditions with AND
    if not conditions:
        return None, None
    
    filter_expression = conditions[0]
    for condition in conditions[1:]:
        filter_expression = filter_expression & condition
    
    return filter_expression, expression_values


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