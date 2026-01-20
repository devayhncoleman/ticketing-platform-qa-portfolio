"""
Main Lambda Handler - Routes requests to appropriate functions
This file serves as the entry point for all API Gateway integrations

Enhanced with:
- Comments/Chat functionality
- Attachment uploads
- User role management
- Tech assignment
- Get current user (for role-based routing)
"""

# Import all function handlers
from functions.create_ticket import handler as create_ticket_handler
from functions.get_ticket import handler as get_ticket_handler
from functions.list_tickets import handler as list_tickets_handler
from functions.update_ticket import handler as update_ticket_handler
from functions.delete_ticket import handler as delete_ticket_handler
from functions.assign_ticket import handler as assign_ticket_handler
from functions.create_comment import handler as create_comment_handler
from functions.list_comments import handler as list_comments_handler
from functions.get_upload_url import handler as get_upload_url_handler
from functions.list_users import handler as list_users_handler
from functions.update_user_role import handler as update_user_role_handler
from functions.get_technicians import handler as get_technicians_handler
from functions.get_user_me import handler as get_user_me_handler


# ===== Ticket Handlers =====

def create_ticket(event, context):
    """POST /tickets - Create a new ticket"""
    return create_ticket_handler(event, context)


def get_ticket(event, context):
    """GET /tickets/{id} - Get a single ticket"""
    return get_ticket_handler(event, context)


def list_tickets(event, context):
    """GET /tickets - List tickets (filtered by user role)"""
    return list_tickets_handler(event, context)


def update_ticket(event, context):
    """PATCH /tickets/{id} - Update ticket status (no content editing)"""
    return update_ticket_handler(event, context)


def delete_ticket(event, context):
    """DELETE /tickets/{id} - Soft delete (CLOSED tickets only)"""
    return delete_ticket_handler(event, context)


def assign_ticket(event, context):
    """POST /tickets/{id}/assign - Assign tech to ticket (Admin only)"""
    return assign_ticket_handler(event, context)


# ===== Comment Handlers =====

def create_comment(event, context):
    """POST /tickets/{id}/comments - Add comment with optional attachments"""
    return create_comment_handler(event, context)


def list_comments(event, context):
    """GET /tickets/{id}/comments - Get ticket conversation"""
    return list_comments_handler(event, context)


# ===== Attachment Handlers =====

def get_upload_url(event, context):
    """POST /attachments/upload-url - Get S3 presigned URL for photo upload"""
    return get_upload_url_handler(event, context)


# ===== User/Admin Handlers =====

def list_users(event, context):
    """GET /users - List all users (Admin only)"""
    return list_users_handler(event, context)


def update_user_role(event, context):
    """PATCH /users/{userId}/role - Change user role (Admin only)"""
    return update_user_role_handler(event, context)


def get_technicians(event, context):
    """GET /technicians - List techs for assignment dropdown"""
    return get_technicians_handler(event, context)


def get_user_me(event, context):
    """GET /users/me - Get current user's profile and role (for routing)"""
    return get_user_me_handler(event, context)