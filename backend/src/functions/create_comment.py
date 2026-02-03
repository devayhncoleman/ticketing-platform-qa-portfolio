"""
Lambda handler for creating comments on tickets
ENHANCED: Multi-tenant support - verifies org access before creating comment
"""
import json
import uuid
import os
from datetime import datetime, timezone
from typing import Dict, Any
import boto3
from botocore.exceptions import ClientError

from auth import extract_user_from_event

# Initialize DynamoDB
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
tickets_table = dynamodb.Table(os.environ.get('TICKETS_TABLE', 'dev-tickets'))
comments_table = dynamodb.Table(os.environ.get('COMMENTS_TABLE', 'dev-comments'))


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for POST /tickets/{ticketId}/comments
    Creates a new comment on a ticket
    
    Multi-tenant behavior:
    - Users can only comment on tickets they can access
    - Platform admins: Can comment on any ticket
    - Org admins/Technicians: Can comment on tickets in their organization
    - Customers: Can only comment on their own tickets
    
    Request body:
    - content: Comment text (required)
    - isInternal: Boolean - internal notes only visible to agents (optional)
    """
    try:
        user = extract_user_from_event(event)
        
        # Get ticket ID from path parameters
        path_params = event.get('pathParameters') or {}
        ticket_id = path_params.get('ticketId')
        
        if not ticket_id:
            return create_response(400, {'error': 'Ticket ID is required'})
        
        # Fetch the ticket to verify access
        ticket_response = tickets_table.get_item(Key={'ticketId': ticket_id})
        
        if 'Item' not in ticket_response:
            return create_response(404, {'error': 'Ticket not found'})
        
        ticket = ticket_response['Item']
        
        # Check authorization (includes org membership check)
        if not user.can_access_ticket(ticket):
            return create_response(403, {
                'error': 'You do not have permission to comment on this ticket'
            })
        
        # Parse request body
        body = json.loads(event.get('body', '{}'))
        content = body.get('content', '').strip()
        
        if not content:
            return create_response(400, {'error': 'Comment content is required'})
        
        # Check if this is an internal note (only agents can create internal notes)
        is_internal = body.get('isInternal', False)
        if is_internal and not user.is_agent:
            return create_response(403, {
                'error': 'Only agents can create internal notes'
            })
        
        # Create comment object
        comment_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        
        comment = {
            'commentId': comment_id,
            'ticketId': ticket_id,
            'orgId': ticket.get('orgId'),  # Inherit org from ticket
            'content': content,
            'isInternal': is_internal,
            'createdBy': user.user_id,
            'createdByEmail': user.email,
            'createdByName': user.full_name,
            'createdByRole': user.role,
            'createdAt': now,
            'updatedAt': now
        }
        
        # Save to DynamoDB
        comments_table.put_item(Item=comment)
        
        # Update ticket's updatedAt timestamp
        tickets_table.update_item(
            Key={'ticketId': ticket_id},
            UpdateExpression='SET updatedAt = :updatedAt',
            ExpressionAttributeValues={':updatedAt': now}
        )
        
        print(f"User {user.email} created comment {comment_id} on ticket {ticket_id}")
        return create_response(201, comment)
        
    except json.JSONDecodeError:
        return create_response(400, {'error': 'Invalid JSON in request body'})
    except ClientError as e:
        error_code = e.response['Error']['Code']
        print(f"DynamoDB error: {error_code} - {e}")
        return create_response(500, {'error': 'Failed to create comment'})
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return create_response(500, {'error': 'Internal server error'})


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