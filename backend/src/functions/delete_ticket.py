"""
Lambda function handler for deleting tickets.
DELETE /tickets/{id}
Implements soft delete by default, with hard delete option for admins.
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
    Lambda handler for DELETE /tickets/{id}
    
    Soft delete: Sets status to CLOSED (default)
    Hard delete: Permanently removes from DynamoDB (admin only, with ?hard=true)
    
    Args:
        event: API Gateway event with ticketId in path parameters
        context: Lambda context
    
    Returns:
        API Gateway response with 204 No Content on success
    """
    try:
        # Extract ticket ID
        path_params = event.get('pathParameters', {})
        ticket_id = path_params.get('id')
        
        if not ticket_id:
            return create_response(400, {'error': 'Ticket ID is required'})
        
        # Check for hard delete flag
        query_params = event.get('queryStringParameters') or {}
        hard_delete = query_params.get('hard', 'false').lower() == 'true'
        
        # Get user info
        user_id = extract_user_id(event)
        user_role = extract_user_role(event)
        
        # Get existing ticket
        try:
            response = table.get_item(Key={'ticketId': ticket_id})
        except ClientError as e:
            print(f"DynamoDB error: {e}")
            return create_response(500, {'error': 'Failed to retrieve ticket'})
        
        if 'Item' not in response:
            return create_response(404, {'error': 'Ticket not found'})
        
        existing_ticket = response['Item']
        
        # Authorization check
        if not is_authorized_to_delete(existing_ticket, user_id, user_role, hard_delete):
            return create_response(403, {
                'error': 'You are not authorized to delete this ticket'
            })
        
        # Perform delete
        if hard_delete:
            # Hard delete - permanently remove
            try:
                table.delete_item(
                    Key={'ticketId': ticket_id},
                    ConditionExpression='attribute_exists(ticketId)'
                )
                print(f"✅ HARD deleted ticket: {ticket_id} by user: {user_id}")
            except ClientError as e:
                if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                    return create_response(404, {'error': 'Ticket not found'})
                raise
        else:
            # Soft delete - set status to CLOSED
            from datetime import datetime, timezone
            now = datetime.now(timezone.utc).isoformat()
            
            try:
                table.update_item(
                    Key={'ticketId': ticket_id},
                    UpdateExpression='SET #status = :status, #updatedAt = :updatedAt, #updatedBy = :updatedBy',
                    ExpressionAttributeNames={
                        '#status': 'status',
                        '#updatedAt': 'updatedAt',
                        '#updatedBy': 'updatedBy'
                    },
                    ExpressionAttributeValues={
                        ':status': 'CLOSED',
                        ':updatedAt': now,
                        ':updatedBy': user_id
                    },
                    ConditionExpression='attribute_exists(ticketId)'
                )
                print(f"✅ SOFT deleted (closed) ticket: {ticket_id} by user: {user_id}")
            except ClientError as e:
                if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                    return create_response(404, {'error': 'Ticket not found'})
                raise
        
        # Return 204 No Content (standard for successful DELETE)
        return {
            'statusCode': 204,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,Authorization',
                'Access-Control-Allow-Methods': 'GET,POST,PUT,PATCH,DELETE,OPTIONS'
            }
        }
        
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")
        return create_response(500, {'error': 'Internal server error'})


def is_authorized_to_delete(
    ticket: Dict[str, Any], 
    user_id: str, 
    user_role: str,
    hard_delete: bool
) -> bool:
    """
    Check if user is authorized to delete this ticket
    
    Rules:
    - Hard delete: ADMIN only
    - Soft delete:
      - ADMIN: Can delete any ticket
      - AGENT: Can delete any ticket
      - CUSTOMER: Can only delete their own tickets
    """
    # Hard delete requires ADMIN
    if hard_delete and user_role != 'ADMIN':
        return False
    
    # Soft delete authorization
    if user_role in ['ADMIN', 'AGENT']:
        return True
    
    if user_role == 'CUSTOMER':
        return ticket.get('createdBy') == user_id
    
    return False


def extract_user_id(event: Dict[str, Any]) -> str:
    """Extract user ID from JWT token"""
    return event.get('requestContext', {}).get('authorizer', {}).get('claims', {}).get('sub', 'test-user-123')


def extract_user_role(event: Dict[str, Any]) -> str:
    """Extract user role from JWT token"""
    return event.get('requestContext', {}).get('authorizer', {}).get('claims', {}).get('custom:role', 'CUSTOMER')


def create_response(status_code: int, body: Dict[str, Any]) -> Dict[str, Any]:
    """Create standardized API Gateway response"""
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,Authorization',
            'Access-Control-Allow-Methods': 'GET,POST,PUT,PATCH,DELETE,OPTIONS'
        },
        'body': json.dumps(body, default=str)
    }