"""
Lambda handler for listing comments on a ticket
Returns chat/conversation history
Filters internal notes for customers
"""
import json
import os
from typing import Dict, Any
import boto3
from botocore.exceptions import ClientError

from auth import extract_user_from_event

# Initialize DynamoDB
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
tickets_table = dynamodb.Table(os.environ.get('TICKETS_TABLE', 'dev-tickets'))
comments_table = dynamodb.Table(os.environ.get('COMMENTS_TABLE', 'dev-ticket-comments'))
users_table = dynamodb.Table(os.environ.get('USERS_TABLE', 'dev-users'))


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for GET /tickets/{id}/comments
    Lists all comments for a ticket (filters internal notes for customers)
    
    Query params:
        - limit: Max number of comments to return (default 50)
    """
    try:
        user = extract_user_from_event(event)
        
        # Get ticket ID from path
        ticket_id = event.get('pathParameters', {}).get('id')
        if not ticket_id:
            return create_response(400, {'error': 'Ticket ID is required'})
        
        # Verify ticket exists
        ticket = tickets_table.get_item(Key={'ticketId': ticket_id}).get('Item')
        if not ticket:
            return create_response(404, {'error': 'Ticket not found'})
        
        # Get user's role
        user_record = users_table.get_item(Key={'userId': user.user_id}).get('Item')
        user_role = user_record.get('role', 'CUSTOMER') if user_record else 'CUSTOMER'
        
        # Check access
        is_owner = ticket.get('createdBy') == user.user_id
        is_assigned = ticket.get('assignedTo') == user.user_id
        is_tech_or_admin = user_role in ['TECH', 'ADMIN']
        
        if not (is_owner or is_assigned or is_tech_or_admin):
            return create_response(403, {'error': 'You do not have access to this ticket'})
        
        # Query comments
        query_params = event.get('queryStringParameters') or {}
        limit = min(int(query_params.get('limit', 50)), 100)
        
        response = comments_table.query(
            KeyConditionExpression='ticketId = :tid',
            ExpressionAttributeValues={':tid': ticket_id},
            ScanIndexForward=True,  # Oldest first (chronological)
            Limit=limit
        )
        
        comments = response.get('Items', [])
        
        # Filter internal notes for customers
        if user_role == 'CUSTOMER':
            comments = [c for c in comments if not c.get('isInternal', False)]
        
        return create_response(200, {
            'ticketId': ticket_id,
            'comments': comments,
            'count': len(comments)
        })
        
    except ClientError as e:
        print(f"DynamoDB error: {e}")
        return create_response(500, {'error': 'Failed to list comments'})
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