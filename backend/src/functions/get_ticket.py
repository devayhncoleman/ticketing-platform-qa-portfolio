"""
Lambda handler for getting a single ticket
ENHANCED: Multi-tenant support - verifies org access
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


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for GET /tickets/{ticketId}
    Retrieves a single ticket by ID with authorization checks
    
    Multi-tenant behavior:
    - Platform admins: Can view any ticket
    - Org admins/Technicians: Can view tickets in their organization
    - Customers: Can only view their own tickets
    """
    try:
        user = extract_user_from_event(event)
        
        # Get ticket ID from path parameters
        path_params = event.get('pathParameters') or {}
        ticket_id = path_params.get('ticketId')
        
        if not ticket_id:
            return create_response(400, {'error': 'Ticket ID is required'})
        
        # Fetch ticket from DynamoDB
        response = tickets_table.get_item(Key={'ticketId': ticket_id})
        
        if 'Item' not in response:
            return create_response(404, {'error': 'Ticket not found'})
        
        ticket = response['Item']
        
        # Check authorization (includes org membership check)
        if not user.can_access_ticket(ticket):
            return create_response(403, {
                'error': 'You do not have permission to view this ticket'
            })
        
        print(f"User {user.email} retrieved ticket {ticket_id}")
        return create_response(200, ticket)
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        print(f"DynamoDB error: {error_code} - {e}")
        return create_response(500, {'error': 'Failed to retrieve ticket'})
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