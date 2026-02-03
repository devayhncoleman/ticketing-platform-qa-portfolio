"""
Lambda handler for assigning tickets to technicians
ENHANCED: Multi-tenant support - verifies org access before assignment
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
    Lambda handler for PUT /tickets/{ticketId}/assign
    Assigns a ticket to a technician
    
    Multi-tenant behavior:
    - Platform admins: Can assign any ticket to any technician
    - Org admins: Can assign tickets in their org to technicians in their org
    - Technicians: Can assign tickets in their org (including to themselves)
    - Customers: Cannot assign tickets
    
    Request body:
    - assignedTo: User ID of the technician to assign
    """
    try:
        user = extract_user_from_event(event)
        
        # Get ticket ID from path parameters
        path_params = event.get('pathParameters') or {}
        ticket_id = path_params.get('ticketId')
        
        if not ticket_id:
            return create_response(400, {'error': 'Ticket ID is required'})
        
        # Fetch existing ticket
        response = tickets_table.get_item(Key={'ticketId': ticket_id})
        
        if 'Item' not in response:
            return create_response(404, {'error': 'Ticket not found'})
        
        ticket = response['Item']
        
        # Check authorization (includes org membership check)
        if not user.can_assign_ticket(ticket):
            return create_response(403, {
                'error': 'You do not have permission to assign this ticket'
            })
        
        # Parse request body
        body = json.loads(event.get('body', '{}'))
        assigned_to = body.get('assignedTo')
        
        if not assigned_to:
            return create_response(400, {'error': 'assignedTo (user ID) is required'})
        
        # Verify the assignee exists and is in the same org (unless platform admin)
        assignee = get_user_by_id(assigned_to)
        if not assignee:
            return create_response(404, {'error': 'Assignee user not found'})
        
        # Verify assignee is in the same org as the ticket
        ticket_org_id = ticket.get('orgId')
        assignee_org_id = assignee.get('orgId')
        
        if not user.is_platform_admin:
            if ticket_org_id and assignee_org_id != ticket_org_id:
                return create_response(400, {
                    'error': 'Cannot assign ticket to user outside the organization'
                })
        
        # Verify assignee has appropriate role (technician, org_admin, or platform_admin)
        assignee_role = assignee.get('role', 'customer').lower()
        if assignee_role not in ['technician', 'org_admin', 'platform_admin', 'admin', 'agent']:
            return create_response(400, {
                'error': 'Tickets can only be assigned to technicians or administrators'
            })
        
        # Build assignee name
        assignee_name = f"{assignee.get('firstName', '')} {assignee.get('lastName', '')}".strip()
        if not assignee_name:
            assignee_name = assignee.get('email', 'Unknown')
        
        # Update ticket
        now = datetime.now(timezone.utc).isoformat()
        
        response = tickets_table.update_item(
            Key={'ticketId': ticket_id},
            UpdateExpression='SET assignedTo = :assignedTo, assignedToName = :assignedToName, #status = :status, updatedAt = :updatedAt, updatedBy = :updatedBy',
            ExpressionAttributeNames={
                '#status': 'status'
            },
            ExpressionAttributeValues={
                ':assignedTo': assigned_to,
                ':assignedToName': assignee_name,
                ':status': 'IN_PROGRESS',  # Auto-update status when assigned
                ':updatedAt': now,
                ':updatedBy': user.user_id
            },
            ReturnValues='ALL_NEW'
        )
        
        updated_ticket = response['Attributes']
        
        print(f"User {user.email} assigned ticket {ticket_id} to {assignee_name}")
        return create_response(200, updated_ticket)
        
    except json.JSONDecodeError:
        return create_response(400, {'error': 'Invalid JSON in request body'})
    except ClientError as e:
        error_code = e.response['Error']['Code']
        print(f"DynamoDB error: {error_code} - {e}")
        return create_response(500, {'error': 'Failed to assign ticket'})
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return create_response(500, {'error': 'Internal server error'})


def get_user_by_id(user_id: str) -> Dict[str, Any]:
    """Fetch user from users table by ID."""
    try:
        response = users_table.get_item(Key={'userId': user_id})
        return response.get('Item')
    except Exception as e:
        print(f"Error fetching user {user_id}: {e}")
        return None


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