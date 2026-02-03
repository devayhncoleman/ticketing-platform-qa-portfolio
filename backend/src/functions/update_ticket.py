"""
Lambda handler for updating tickets
ENHANCED: Multi-tenant support - verifies org access before updates
"""
import json
import os
from datetime import datetime, timezone
from typing import Dict, Any
import boto3
from botocore.exceptions import ClientError

from auth import extract_user_from_event

# Initialize DynamoDB
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
tickets_table = dynamodb.Table(os.environ.get('TICKETS_TABLE', 'dev-tickets'))


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for PUT /tickets/{ticketId}
    Updates an existing ticket with authorization checks
    
    Multi-tenant behavior:
    - Platform admins: Can update any ticket
    - Org admins/Technicians: Can update tickets in their organization
    - Customers: Can only update their own tickets (limited fields)
    
    Updatable fields:
    - All users: title, description, priority, category, tags
    - Agents only: status, assignedTo
    """
    try:
        user = extract_user_from_event(event)
        
        # Get ticket ID from path parameters
        path_params = event.get('pathParameters') or {}
        ticket_id = path_params.get('ticketId')
        
        if not ticket_id:
            return create_response(400, {'error': 'Ticket ID is required'})
        
        # Fetch existing ticket
        response = tickets_table.get_item(Key={'ticketId': ticket_id})
        
        if 'Item' not in response:
            return create_response(404, {'error': 'Ticket not found'})
        
        ticket = response['Item']
        
        # Check authorization (includes org membership check)
        if not user.can_update_ticket(ticket):
            return create_response(403, {
                'error': 'You do not have permission to update this ticket'
            })
        
        # Parse request body
        body = json.loads(event.get('body', '{}'))
        
        if not body:
            return create_response(400, {'error': 'Request body is required'})
        
        # Build update expression
        update_parts, expression_values = build_update_expression(user, body, ticket)
        
        if not update_parts:
            return create_response(400, {'error': 'No valid fields to update'})
        
        # Add metadata
        now = datetime.now(timezone.utc).isoformat()
        update_parts.append('updatedAt = :updatedAt')
        update_parts.append('updatedBy = :updatedBy')
        expression_values[':updatedAt'] = now
        expression_values[':updatedBy'] = user.user_id
        
        # Execute update
        update_expression = 'SET ' + ', '.join(update_parts)
        
        response = tickets_table.update_item(
            Key={'ticketId': ticket_id},
            UpdateExpression=update_expression,
            ExpressionAttributeValues=expression_values,
            ReturnValues='ALL_NEW'
        )
        
        updated_ticket = response['Attributes']
        
        print(f"User {user.email} updated ticket {ticket_id}")
        return create_response(200, updated_ticket)
        
    except json.JSONDecodeError:
        return create_response(400, {'error': 'Invalid JSON in request body'})
    except ClientError as e:
        error_code = e.response['Error']['Code']
        print(f"DynamoDB error: {error_code} - {e}")
        return create_response(500, {'error': 'Failed to update ticket'})
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return create_response(500, {'error': 'Internal server error'})


def build_update_expression(user, body: Dict[str, Any], existing_ticket: Dict[str, Any]):
    """
    Build DynamoDB update expression based on user role and request body.
    
    Returns:
        Tuple of (update_parts list, expression_values dict)
    """
    update_parts = []
    expression_values = {}
    
    # Fields anyone can update (on their own tickets)
    general_fields = ['title', 'description', 'priority', 'category', 'tags']
    
    # Fields only agents can update
    agent_fields = ['status', 'assignedTo', 'assignedToName']
    
    # Process general fields
    for field in general_fields:
        if field in body:
            value = body[field]
            
            # Validate priority
            if field == 'priority':
                value = value.upper()
                valid_priorities = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']
                if value not in valid_priorities:
                    continue  # Skip invalid values
            
            # Validate title/description not empty
            if field in ['title', 'description']:
                if not value or not str(value).strip():
                    continue
                value = str(value).strip()
            
            update_parts.append(f'{field} = :{field}')
            expression_values[f':{field}'] = value
    
    # Process agent-only fields
    if user.is_agent:
        for field in agent_fields:
            if field in body:
                value = body[field]
                
                # Validate status
                if field == 'status':
                    value = value.upper()
                    valid_statuses = ['OPEN', 'IN_PROGRESS', 'RESOLVED', 'CLOSED']
                    if value not in valid_statuses:
                        continue
                
                update_parts.append(f'{field} = :{field}')
                expression_values[f':{field}'] = value
    
    return update_parts, expression_values


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