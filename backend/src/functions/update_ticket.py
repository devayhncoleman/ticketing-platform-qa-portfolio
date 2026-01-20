"""
Lambda handler for updating tickets
Updated: Uses Cognito JWT for real user authentication and authorization
"""
import json
import os
from datetime import datetime, timezone
from typing import Dict, Any, List
import boto3
from botocore.exceptions import ClientError

# Import auth utilities
from auth import extract_user_from_event, UserContext

# Initialize DynamoDB
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
table_name = os.environ.get('TICKETS_TABLE_NAME', 'dev-tickets')
table = dynamodb.Table(table_name)

# Valid values for constrained fields
VALID_STATUSES = ['OPEN', 'IN_PROGRESS', 'WAITING', 'RESOLVED', 'CLOSED']
VALID_PRIORITIES = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']

# Fields that can be updated
ALLOWED_FIELDS = ['title', 'description', 'status', 'priority', 'category', 
                  'assignedTo', 'tags', 'resolution']


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for PATCH /tickets/{id}
    Updates a ticket with authorization check and optimistic locking
    """
    try:
        # Extract authenticated user from Cognito JWT
        user = extract_user_from_event(event)
        
        # Get ticket ID from path
        path_params = event.get('pathParameters') or {}
        ticket_id = path_params.get('id')
        
        if not ticket_id:
            return create_response(400, {'error': 'Ticket ID is required'})
        
        # Parse request body
        body = json.loads(event.get('body', '{}'))
        
        if not body:
            return create_response(400, {'error': 'Request body is required'})
        
        # Fetch existing ticket
        response = table.get_item(Key={'ticketId': ticket_id})
        existing_ticket = response.get('Item')
        
        if not existing_ticket:
            return create_response(404, {'error': f'Ticket {ticket_id} not found'})
        
        # Check authorization
        if not user.can_update_ticket(existing_ticket):
            print(f"Access denied: User {user.email} cannot update ticket {ticket_id}")
            return create_response(403, {'error': 'You do not have permission to update this ticket'})
        
        # Validate fields
        validation_error = validate_update_fields(body)
        if validation_error:
            return create_response(400, {'error': validation_error})
        
        # Build update expression
        now = datetime.now(timezone.utc).isoformat()
        update_parts = []
        expression_values = {
            ':updatedAt': now,
            ':updatedBy': user.user_id
        }
        expression_names = {}
        
        # Add each field to update
        for field, value in body.items():
            if field in ALLOWED_FIELDS:
                # Handle reserved words
                attr_name = f'#{field}'
                attr_value = f':{field}'
                expression_names[attr_name] = field
                expression_values[attr_value] = value.upper() if field in ['status', 'priority'] else value
                update_parts.append(f'{attr_name} = {attr_value}')
        
        # Always update timestamps
        update_parts.append('updatedAt = :updatedAt')
        update_parts.append('updatedBy = :updatedBy')
        
        # Auto-set resolvedAt when status changes to RESOLVED
        if body.get('status', '').upper() == 'RESOLVED' and existing_ticket.get('status') != 'RESOLVED':
            update_parts.append('resolvedAt = :resolvedAt')
            expression_values[':resolvedAt'] = now
        
        update_expression = 'SET ' + ', '.join(update_parts)
        
        # Optimistic locking - check updatedAt hasn't changed
        condition_expression = 'updatedAt = :existingUpdatedAt'
        expression_values[':existingUpdatedAt'] = existing_ticket['updatedAt']
        
        try:
            # Perform conditional update
            update_response = table.update_item(
                Key={'ticketId': ticket_id},
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expression_values,
                ExpressionAttributeNames=expression_names if expression_names else None,
                ConditionExpression=condition_expression,
                ReturnValues='ALL_NEW'
            )
            
            updated_ticket = update_response['Attributes']
            print(f"User {user.email} updated ticket {ticket_id}")
            return create_response(200, updated_ticket)
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                return create_response(409, {
                    'error': 'Ticket was modified by another user. Please refresh and try again.'
                })
            raise
        
    except json.JSONDecodeError:
        return create_response(400, {'error': 'Invalid JSON in request body'})
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        print(f"DynamoDB error: {error_code} - {e}")
        return create_response(500, {'error': 'Failed to update ticket'})
        
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return create_response(500, {'error': 'Internal server error'})


def validate_update_fields(body: Dict[str, Any]) -> str:
    """
    Validate update request fields.
    Returns error message if invalid, None if valid.
    """
    # Check for unknown fields
    unknown_fields = [f for f in body.keys() if f not in ALLOWED_FIELDS]
    if unknown_fields:
        return f"Unknown fields: {', '.join(unknown_fields)}"
    
    # Validate status
    if 'status' in body:
        status = body['status'].upper()
        if status not in VALID_STATUSES:
            return f"Invalid status. Must be one of: {', '.join(VALID_STATUSES)}"
    
    # Validate priority
    if 'priority' in body:
        priority = body['priority'].upper()
        if priority not in VALID_PRIORITIES:
            return f"Invalid priority. Must be one of: {', '.join(VALID_PRIORITIES)}"
    
    # Validate tags is a list
    if 'tags' in body and not isinstance(body['tags'], list):
        return "Tags must be an array"
    
    return None


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