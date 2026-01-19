"""
Lambda function handler for retrieving a single ticket.
GET /tickets/{id}
"""
import json
import os
from typing import Dict, Any
import boto3
from botocore.exceptions import ClientError


# Initialize DynamoDB
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
table_name = os.environ.get('TICKETS_TABLE_NAME', 'dev-tickets')
table = dynamodb.Table(table_name)


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for GET /tickets/{id}
    Retrieves a single ticket by ID with authorization checks
    
    Args:
        event: API Gateway event with ticketId in path parameters
        context: Lambda context
    
    Returns:
        API Gateway response with ticket data or error
    """
    try:
        # Extract ticket ID from path parameters
        path_params = event.get('pathParameters', {})
        ticket_id = path_params.get('id')
        
        if not ticket_id:
            return create_response(400, {'error': 'Ticket ID is required'})
        
        # Get user info from JWT
        user_id = extract_user_id(event)
        user_role = extract_user_role(event)
        
        # Retrieve ticket from DynamoDB
        try:
            response = table.get_item(Key={'ticketId': ticket_id})
        except ClientError as e:
            error_code = e.response['Error']['Code']
            print(f"DynamoDB error: {error_code} - {e}")
            return create_response(500, {'error': 'Failed to retrieve ticket'})
        
        # Check if ticket exists
        if 'Item' not in response:
            return create_response(404, {'error': 'Ticket not found'})
        
        ticket = response['Item']
        
        # Authorization check
        if not is_authorized(ticket, user_id, user_role):
            return create_response(403, {
                'error': 'You are not authorized to view this ticket'
            })
        
        print(f"✅ Retrieved ticket: {ticket_id} for user: {user_id}")
        
        return create_response(200, ticket)
        
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")
        return create_response(500, {'error': 'Internal server error'})


def is_authorized(ticket: Dict[str, Any], user_id: str, user_role: str) -> bool:
    """
    Check if user is authorized to view this ticket
    
    Rules:
    - ADMIN: Can view all tickets
    - AGENT: Can view all tickets
    - CUSTOMER: Can only view their own tickets
    
    Args:
        ticket: The ticket data
        user_id: Current user's ID
        user_role: Current user's role (ADMIN, AGENT, CUSTOMER)
    
    Returns:
        True if authorized, False otherwise
    """
    # Admins and agents can view all tickets
    if user_role in ['ADMIN', 'AGENT']:
        return True
    
    # Customers can only view their own tickets
    if user_role == 'CUSTOMER':
        return ticket.get('createdBy') == user_id
    
    # Unknown role - deny by default
    return False


def extract_user_id(event: Dict[str, Any]) -> str:
    """
    Extract user ID from JWT token in event
    TODO: Implement real JWT parsing when Cognito is set up
    """
    # For now, return test user ID
    # In production, this would parse the JWT from authorizer context
    return event.get('requestContext', {}).get('authorizer', {}).get('claims', {}).get('sub', 'test-user-123')


def extract_user_role(event: Dict[str, Any]) -> str:
    """
    Extract user role from JWT token in event
    TODO: Implement real JWT parsing when Cognito is set up
    """
    # For now, return test role
    # In production, this would parse custom:role from JWT claims
    return event.get('requestContext', {}).get('authorizer', {}).get('claims', {}).get('custom:role', 'CUSTOMER')


def create_response(status_code: int, body: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create standardized API Gateway response
    """
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