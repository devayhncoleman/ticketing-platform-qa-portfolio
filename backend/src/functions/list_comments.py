"""
Lambda handler for listing comments on a ticket
ENHANCED: Multi-tenant support - verifies org access and filters internal notes
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
comments_table = dynamodb.Table(os.environ.get('COMMENTS_TABLE', 'dev-comments'))


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for GET /tickets/{ticketId}/comments
    Lists all comments on a ticket
    
    Multi-tenant behavior:
    - Users can only see comments on tickets they can access
    - Internal notes (isInternal=true) are only visible to agents
    - Platform admins: Can see all comments on any ticket
    - Org admins/Technicians: Can see all comments in their organization
    - Customers: Can only see non-internal comments on their own tickets
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
                'error': 'You do not have permission to view comments on this ticket'
            })
        
        # Query comments for this ticket
        # Note: For production, use a GSI on ticketId for efficient queries
        response = comments_table.scan(
            FilterExpression=Attr('ticketId').eq(ticket_id)
        )
        comments = response.get('Items', [])
        
        # Handle pagination
        while 'LastEvaluatedKey' in response:
            response = comments_table.scan(
                FilterExpression=Attr('ticketId').eq(ticket_id),
                ExclusiveStartKey=response['LastEvaluatedKey']
            )
            comments.extend(response.get('Items', []))
        
        # Filter out internal notes for non-agents
        if not user.is_agent:
            comments = [c for c in comments if not c.get('isInternal', False)]
        
        # Sort by createdAt ascending (oldest first for conversation flow)
        comments.sort(key=lambda x: x.get('createdAt', ''))
        
        print(f"User {user.email} retrieved {len(comments)} comments for ticket {ticket_id}")
        
        return create_response(200, {
            'comments': comments,
            'count': len(comments),
            'ticketId': ticket_id
        })
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        print(f"DynamoDB error: {error_code} - {e}")
        return create_response(500, {'error': 'Failed to retrieve comments'})
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