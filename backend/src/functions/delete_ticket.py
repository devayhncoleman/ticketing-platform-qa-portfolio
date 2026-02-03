"""
Lambda handler for deleting tickets
ENHANCED: Multi-tenant support - verifies org access before deletion
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
    Lambda handler for DELETE /tickets/{ticketId}
    Soft deletes a ticket by setting status to DELETED
    
    Multi-tenant behavior:
    - Platform admins: Can delete any ticket (including hard delete)
    - Org admins: Can delete tickets in their organization
    - Technicians: Can delete tickets in their organization
    - Customers: Can only delete their own tickets
    
    Query parameters:
    - hard: If 'true', permanently deletes (platform_admin only)
    """
    try:
        user = extract_user_from_event(event)
        
        # Get ticket ID from path parameters
        path_params = event.get('pathParameters') or {}
        ticket_id = path_params.get('ticketId')
        
        if not ticket_id:
            return create_response(400, {'error': 'Ticket ID is required'})
        
        # Check for hard delete flag
        query_params = event.get('queryStringParameters') or {}
        hard_delete = query_params.get('hard', '').lower() == 'true'
        
        # Fetch existing ticket
        response = tickets_table.get_item(Key={'ticketId': ticket_id})
        
        if 'Item' not in response:
            return create_response(404, {'error': 'Ticket not found'})
        
        ticket = response['Item']
        
        # Check authorization (includes org membership check)
        if not user.can_delete_ticket(ticket, hard_delete=hard_delete):
            if hard_delete:
                return create_response(403, {
                    'error': 'Only platform administrators can permanently delete tickets'
                })
            return create_response(403, {
                'error': 'You do not have permission to delete this ticket'
            })
        
        if hard_delete:
            # Permanently delete from database
            tickets_table.delete_item(Key={'ticketId': ticket_id})
            print(f"User {user.email} HARD DELETED ticket {ticket_id}")
            return create_response(200, {
                'message': 'Ticket permanently deleted',
                'ticketId': ticket_id
            })
        else:
            # Soft delete - mark as DELETED
            now = datetime.now(timezone.utc).isoformat()
            
            response = tickets_table.update_item(
                Key={'ticketId': ticket_id},
                UpdateExpression='SET #status = :status, updatedAt = :updatedAt, updatedBy = :updatedBy, deletedAt = :deletedAt, deletedBy = :deletedBy',
                ExpressionAttributeNames={
                    '#status': 'status'
                },
                ExpressionAttributeValues={
                    ':status': 'DELETED',
                    ':updatedAt': now,
                    ':updatedBy': user.user_id,
                    ':deletedAt': now,
                    ':deletedBy': user.user_id
                },
                ReturnValues='ALL_NEW'
            )
            
            print(f"User {user.email} soft deleted ticket {ticket_id}")
            return create_response(200, {
                'message': 'Ticket deleted',
                'ticket': response['Attributes']
            })
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        print(f"DynamoDB error: {error_code} - {e}")
        return create_response(500, {'error': 'Failed to delete ticket'})
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