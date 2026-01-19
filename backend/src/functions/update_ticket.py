"""
Lambda function handler for updating tickets.
PATCH /tickets/{id}
Implements optimistic locking to prevent concurrent modification conflicts.
"""
import json
import os
from datetime import datetime, timezone
from typing import Dict, Any, Optional
import boto3
from botocore.exceptions import ClientError


# Initialize DynamoDB
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
table_name = os.environ.get('TICKETS_TABLE_NAME', 'dev-tickets')
table = dynamodb.Table(table_name)


# Allowed fields for update (prevents updating immutable fields)
UPDATABLE_FIELDS = {
    'status', 'priority', 'assignedTo', 'resolution', 'tags', 'category'
}

VALID_STATUSES = ['OPEN', 'IN_PROGRESS', 'WAITING', 'RESOLVED', 'CLOSED']
VALID_PRIORITIES = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for PATCH /tickets/{id}
    Updates ticket with authorization and validation
    
    Updateable fields:
    - status: Ticket status (OPEN, IN_PROGRESS, WAITING, RESOLVED, CLOSED)
    - priority: Ticket priority (LOW, MEDIUM, HIGH, CRITICAL)
    - assignedTo: Agent ID to assign ticket
    - resolution: Resolution description (required when status=RESOLVED)
    - tags: List of tags
    - category: Ticket category
    
    Args:
        event: API Gateway event with ticketId and update data
        context: Lambda context
    
    Returns:
        API Gateway response with updated ticket
    """
    try:
        # Extract ticket ID
        path_params = event.get('pathParameters', {})
        ticket_id = path_params.get('id')
        
        if not ticket_id:
            return create_response(400, {'error': 'Ticket ID is required'})
        
        # Parse request body
        body = json.loads(event.get('body', '{}'))
        
        if not body:
            return create_response(400, {'error': 'Update data is required'})
        
        # Get user info
        user_id = extract_user_id(event)
        user_role = extract_user_role(event)
        
        # Get existing ticket
        try:
            response = table.get_item(Key={'ticketId': ticket_id})
        except ClientError as e:
            print(f"DynamoDB error: {e}")
            return create_response(500, {'error': 'Failed to retrieve ticket'})
        
        if 'Item' not in response:
            return create_response(404, {'error': 'Ticket not found'})
        
        existing_ticket = response['Item']
        
        # Authorization check
        if not is_authorized_to_update(existing_ticket, user_id, user_role):
            return create_response(403, {
                'error': 'You are not authorized to update this ticket'
            })
        
        # Validate update fields
        validation_error = validate_update_fields(body, existing_ticket)
        if validation_error:
            return create_response(400, {'error': validation_error})
        
        # Build update expression
        update_expr, expr_attr_names, expr_attr_values = build_update_expression(
            body, user_id
        )
        
        # Update with optimistic locking (using updatedAt as version)
        try:
            response = table.update_item(
                Key={'ticketId': ticket_id},
                UpdateExpression=update_expr,
                ExpressionAttributeNames=expr_attr_names,
                ExpressionAttributeValues=expr_attr_values,
                ConditionExpression='attribute_exists(ticketId)',  # Ensure ticket exists
                ReturnValues='ALL_NEW'
            )
            
            updated_ticket = response['Attributes']
            
            print(f"✅ Updated ticket: {ticket_id} by user: {user_id}")
            
            return create_response(200, updated_ticket)
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                return create_response(409, {
                    'error': 'Ticket was modified by another process. Please refresh and try again.'
                })
            print(f"DynamoDB error: {e}")
            return create_response(500, {'error': 'Failed to update ticket'})
        
    except json.JSONDecodeError:
        return create_response(400, {'error': 'Invalid JSON in request body'})
    
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")
        return create_response(500, {'error': 'Internal server error'})


def is_authorized_to_update(ticket: Dict[str, Any], user_id: str, user_role: str) -> bool:
    """
    Check if user is authorized to update this ticket
    
    Rules:
    - ADMIN: Can update all tickets
    - AGENT: Can update all tickets
    - CUSTOMER: Can only update their own tickets (limited fields)
    """
    if user_role in ['ADMIN', 'AGENT']:
        return True
    
    if user_role == 'CUSTOMER':
        return ticket.get('createdBy') == user_id
    
    return False


def validate_update_fields(updates: Dict[str, Any], existing_ticket: Dict[str, Any]) -> Optional[str]:
    """
    Validate update fields
    
    Returns:
        Error message if validation fails, None if valid
    """
    # Check for invalid fields
    invalid_fields = set(updates.keys()) - UPDATABLE_FIELDS
    if invalid_fields:
        return f"Invalid fields: {', '.join(invalid_fields)}. Allowed fields: {', '.join(UPDATABLE_FIELDS)}"
    
    # Validate status
    if 'status' in updates:
        status = updates['status'].upper()
        if status not in VALID_STATUSES:
            return f"Invalid status. Must be one of: {', '.join(VALID_STATUSES)}"
        
        # If setting to RESOLVED, resolution is required
        if status == 'RESOLVED' and not updates.get('resolution'):
            return "Resolution is required when status is RESOLVED"
    
    # Validate priority
    if 'priority' in updates:
        priority = updates['priority'].upper()
        if priority not in VALID_PRIORITIES:
            return f"Invalid priority. Must be one of: {', '.join(VALID_PRIORITIES)}"
    
    # Validate tags (must be list)
    if 'tags' in updates:
        if not isinstance(updates['tags'], list):
            return "Tags must be an array"
    
    return None


def build_update_expression(
    updates: Dict[str, Any], 
    user_id: str
) -> tuple[str, Dict[str, str], Dict[str, Any]]:
    """
    Build DynamoDB update expression from update fields
    
    Returns:
        (UpdateExpression, ExpressionAttributeNames, ExpressionAttributeValues)
    """
    update_parts = []
    expr_attr_names = {}
    expr_attr_values = {}
    
    # Add user-provided fields
    for i, (field, value) in enumerate(updates.items()):
        if field in UPDATABLE_FIELDS:
            placeholder = f"#field{i}"
            value_placeholder = f":val{i}"
            
            # Uppercase status and priority
            if field in ['status', 'priority']:
                value = value.upper()
            
            update_parts.append(f"{placeholder} = {value_placeholder}")
            expr_attr_names[placeholder] = field
            expr_attr_values[value_placeholder] = value
    
    # Always update metadata
    now = datetime.now(timezone.utc).isoformat()
    update_parts.append("#updatedAt = :updatedAt")
    update_parts.append("#updatedBy = :updatedBy")
    
    expr_attr_names["#updatedAt"] = "updatedAt"
    expr_attr_names["#updatedBy"] = "updatedBy"
    expr_attr_values[":updatedAt"] = now
    expr_attr_values[":updatedBy"] = user_id
    
    # If status is RESOLVED, set resolvedAt
    if 'status' in updates and updates['status'].upper() == 'RESOLVED':
        update_parts.append("#resolvedAt = :resolvedAt")
        expr_attr_names["#resolvedAt"] = "resolvedAt"
        expr_attr_values[":resolvedAt"] = now
    
    update_expr = "SET " + ", ".join(update_parts)
    
    return update_expr, expr_attr_names, expr_attr_values


def extract_user_id(event: Dict[str, Any]) -> str:
    """Extract user ID from JWT token"""
    return event.get('requestContext', {}).get('authorizer', {}).get('claims', {}).get('sub', 'test-user-123')


def extract_user_role(event: Dict[str, Any]) -> str:
    """Extract user role from JWT token"""
    return event.get('requestContext', {}).get('authorizer', {}).get('claims', {}).get('custom:role', 'CUSTOMER')


def create_response(status_code: int, body: Dict[str, Any]) -> Dict[str, Any]:
    """Create standardized API Gateway response"""
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,Authorization',
            'Access-Control-Allow-Methods': 'GET,POST,PUT,PATCH,DELETE,OPTIONS'
        },
        'body': json.dumps(body, default=str)
    }