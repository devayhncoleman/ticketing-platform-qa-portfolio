"""
Lambda handler for deleting tickets (soft and hard delete)
Updated: Uses Cognito JWT for real user authentication and authorization
"""
import json
import os
from datetime import datetime, timezone
from typing import Dict, Any
import boto3
from botocore.exceptions import ClientError

# Import auth utilities
from auth import extract_user_from_event, UserContext

# Initialize DynamoDB
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
table_name = os.environ.get('TICKETS_TABLE_NAME', 'dev-tickets')
table = dynamodb.Table(table_name)


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for DELETE /tickets/{id}
    
    Supports two modes:
    - Soft delete (default): Sets status to CLOSED, preserves audit trail
    - Hard delete (?hard=true): Permanently removes from database (ADMIN only)
    
    Authorization:
    - Soft delete: User can delete their own tickets, agents can delete any
    - Hard delete: Admin only
    """
    try:
        # Extract authenticated user from Cognito JWT
        user = extract_user_from_event(event)
        
        # Get ticket ID from path
        path_params = event.get('pathParameters') or {}
        ticket_id = path_params.get('id')
        
        if not ticket_id:
            return create_response(400, {'error': 'Ticket ID is required'})
        
        # Check if hard delete requested
        query_params = event.get('queryStringParameters') or {}
        hard_delete = query_params.get('hard', '').lower() == 'true'
        
        # Fetch existing ticket
        response = table.get_item(Key={'ticketId': ticket_id})
        existing_ticket = response.get('Item')
        
        if not existing_ticket:
            return create_response(404, {'error': f'Ticket {ticket_id} not found'})
        
        # Check authorization
        if not user.can_delete_ticket(existing_ticket, hard_delete=hard_delete):
            if hard_delete:
                print(f"Access denied: User {user.email} cannot hard delete ticket {ticket_id}")
                return create_response(403, {'error': 'Only administrators can permanently delete tickets'})
            else:
                print(f"Access denied: User {user.email} cannot delete ticket {ticket_id}")
                return create_response(403, {'error': 'You do not have permission to delete this ticket'})
        
        if hard_delete:
            # Permanent deletion (Admin only)
            table.delete_item(Key={'ticketId': ticket_id})
            print(f"User {user.email} HARD DELETED ticket {ticket_id}")
            return create_response(204, {})
        else:
            # Soft delete - set status to CLOSED
            now = datetime.now(timezone.utc).isoformat()
            
            table.update_item(
                Key={'ticketId': ticket_id},
                UpdateExpression='SET #status = :status, updatedAt = :updatedAt, updatedBy = :updatedBy, closedAt = :closedAt, closedBy = :closedBy',
                ExpressionAttributeNames={'#status': 'status'},
                ExpressionAttributeValues={
                    ':status': 'CLOSED',
                    ':updatedAt': now,
                    ':updatedBy': user.user_id,
                    ':closedAt': now,
                    ':closedBy': user.user_id
                }
            )
            
            print(f"User {user.email} soft deleted ticket {ticket_id}")
            return create_response(204, {})
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        print(f"DynamoDB error: {error_code} - {e}")
        return create_response(500, {'error': 'Failed to delete ticket'})
        
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return create_response(500, {'error': 'Internal server error'})


def create_response(status_code: int, body: Dict[str, Any]) -> Dict[str, Any]:
    """Create standardized API Gateway response."""
    # For 204 No Content, body should be empty
    response = {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,Authorization',
            'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS'
        }
    }
    
    if status_code != 204:
        response['body'] = json.dumps(body, default=str)
    
    return response