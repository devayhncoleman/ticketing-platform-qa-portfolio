"""
Lambda handler for assigning tickets to technicians
Only ADMIN users can assign tickets
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
users_table = dynamodb.Table(os.environ.get('USERS_TABLE', 'dev-users'))


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for POST /tickets/{id}/assign
    Assigns a technician to a ticket (Admin only)
    
    Request body:
        - technicianId: User ID of the technician to assign
    """
    try:
        user = extract_user_from_event(event)
        
        # Check if user is admin (get role from users table)
        user_record = users_table.get_item(Key={'userId': user.user_id}).get('Item')
        if not user_record or user_record.get('role') != 'ADMIN':
            return create_response(403, {'error': 'Only administrators can assign tickets'})
        
        # Get ticket ID from path
        ticket_id = event.get('pathParameters', {}).get('id')
        if not ticket_id:
            return create_response(400, {'error': 'Ticket ID is required'})
        
        # Parse request body
        body = json.loads(event.get('body', '{}'))
        technician_id = body.get('technicianId')
        
        if not technician_id:
            return create_response(400, {'error': 'Technician ID is required'})
        
        # Verify technician exists and has TECH role
        tech_record = users_table.get_item(Key={'userId': technician_id}).get('Item')
        if not tech_record:
            return create_response(404, {'error': 'Technician not found'})
        if tech_record.get('role') not in ['TECH', 'ADMIN']:
            return create_response(400, {'error': 'User is not a technician'})
        
        # Update ticket
        now = datetime.now(timezone.utc).isoformat()
        
        response = tickets_table.update_item(
            Key={'ticketId': ticket_id},
            UpdateExpression='SET assignedTo = :tech, assignedToName = :name, updatedAt = :now, updatedBy = :user',
            ExpressionAttributeValues={
                ':tech': technician_id,
                ':name': f"{tech_record.get('firstName', '')} {tech_record.get('lastName', '')}".strip(),
                ':now': now,
                ':user': user.user_id
            },
            ReturnValues='ALL_NEW'
        )
        
        updated_ticket = response.get('Attributes', {})
        print(f"Ticket {ticket_id} assigned to {technician_id} by admin {user.email}")
        
        return create_response(200, updated_ticket)
        
    except json.JSONDecodeError:
        return create_response(400, {'error': 'Invalid JSON in request body'})
    except ClientError as e:
        print(f"DynamoDB error: {e}")
        return create_response(500, {'error': 'Failed to assign ticket'})
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