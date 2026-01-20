"""
Lambda handler for creating comments on tickets
Supports the chat/conversation feature between customer and tech
Can include photo attachments (S3 URLs)
"""
import json
import uuid
import os
from datetime import datetime, timezone
from typing import Dict, Any
import boto3
from botocore.exceptions import ClientError

from auth import extract_user_from_event

# Initialize AWS resources
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
tickets_table = dynamodb.Table(os.environ.get('TICKETS_TABLE', 'dev-tickets'))
comments_table = dynamodb.Table(os.environ.get('COMMENTS_TABLE', 'dev-ticket-comments'))
users_table = dynamodb.Table(os.environ.get('USERS_TABLE', 'dev-users'))


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for POST /tickets/{id}/comments
    Creates a new comment/message on a ticket
    
    Request body:
        - content: The comment text (required)
        - attachments: List of S3 URLs for photos (optional)
        - isInternal: Boolean - if true, only visible to techs/admins (optional)
    """
    try:
        user = extract_user_from_event(event)
        
        # Get ticket ID from path
        ticket_id = event.get('pathParameters', {}).get('id')
        if not ticket_id:
            return create_response(400, {'error': 'Ticket ID is required'})
        
        # Verify ticket exists and user has access
        ticket = tickets_table.get_item(Key={'ticketId': ticket_id}).get('Item')
        if not ticket:
            return create_response(404, {'error': 'Ticket not found'})
        
        # Get user's role
        user_record = users_table.get_item(Key={'userId': user.user_id}).get('Item')
        user_role = user_record.get('role', 'CUSTOMER') if user_record else 'CUSTOMER'
        
        # Check access: Customer can only comment on their own tickets
        # Techs can comment on assigned tickets, Admins can comment on any
        is_owner = ticket.get('createdBy') == user.user_id
        is_assigned = ticket.get('assignedTo') == user.user_id
        is_tech_or_admin = user_role in ['TECH', 'ADMIN']
        
        if not (is_owner or is_assigned or is_tech_or_admin):
            return create_response(403, {'error': 'You do not have access to this ticket'})
        
        # Parse request body
        body = json.loads(event.get('body', '{}'))
        content = body.get('content', '').strip()
        
        if not content:
            return create_response(400, {'error': 'Comment content is required'})
        
        # Validate attachments (must be valid S3 URLs, max 5 photos)
        attachments = body.get('attachments', [])
        if len(attachments) > 5:
            return create_response(400, {'error': 'Maximum 5 attachments per comment'})
        
        # Validate attachment URLs (basic check)
        bucket_name = os.environ.get('ATTACHMENTS_BUCKET', '')
        for url in attachments:
            if not isinstance(url, str) or (bucket_name and bucket_name not in url):
                return create_response(400, {'error': 'Invalid attachment URL'})
        
        # Internal comments only allowed for tech/admin
        is_internal = body.get('isInternal', False)
        if is_internal and user_role == 'CUSTOMER':
            is_internal = False  # Customers can't create internal notes
        
        # Create comment
        comment_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        
        comment = {
            'ticketId': ticket_id,
            'commentId': comment_id,
            'content': content,
            'authorId': user.user_id,
            'authorEmail': user.email,
            'authorName': f"{user_record.get('firstName', '')} {user_record.get('lastName', '')}".strip() if user_record else user.email,
            'authorRole': user_role,
            'attachments': attachments,
            'isInternal': is_internal,
            'createdAt': now
        }
        
        # Save comment
        comments_table.put_item(Item=comment)
        
        # Update ticket's updatedAt timestamp
        tickets_table.update_item(
            Key={'ticketId': ticket_id},
            UpdateExpression='SET updatedAt = :now, lastCommentAt = :now',
            ExpressionAttributeValues={':now': now}
        )
        
        print(f"Comment {comment_id} created on ticket {ticket_id} by {user.email}")
        return create_response(201, comment)
        
    except json.JSONDecodeError:
        return create_response(400, {'error': 'Invalid JSON in request body'})
    except ClientError as e:
        print(f"DynamoDB error: {e}")
        return create_response(500, {'error': 'Failed to create comment'})
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