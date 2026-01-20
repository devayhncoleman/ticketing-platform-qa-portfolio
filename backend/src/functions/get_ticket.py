"""
Lambda handler for getting a single ticket by ID
Updated: Uses Cognito JWT for real user authentication and authorization
"""
import json
import os
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
    Lambda handler for GET /tickets/{id}
    Retrieves a single ticket by ID with authorization check
    
    Args:
        event: API Gateway event with ticketId in path
        context: Lambda context
        
    Returns:
        API Gateway response with ticket data or error
    """
    try:
        # Extract authenticated user from Cognito JWT
        user = extract_user_from_event(event)
        
        # Get ticket ID from path parameters
        path_params = event.get('pathParameters') or {}
        ticket_id = path_params.get('id')
        
        if not ticket_id:
            return create_response(400, {'error': 'Ticket ID is required'})
        
        # Fetch ticket from DynamoDB
        response = table.get_item(Key={'ticketId': ticket_id})
        ticket = response.get('Item')
        
        if not ticket:
            return create_response(404, {'error': f'Ticket {ticket_id} not found'})
        
        # Check authorization - customers can only see their own tickets
        if not user.can_access_ticket(ticket):
            print(f"Access denied: User {user.email} cannot access ticket {ticket_id}")
            return create_response(403, {'error': 'You do not have permission to view this ticket'})
        
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