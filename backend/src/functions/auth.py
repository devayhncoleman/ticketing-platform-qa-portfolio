"""
Authentication utilities for extracting user info from Cognito JWT tokens.
Used by all Lambda functions to get authenticated user context.

ENHANCED: Added multi-tenant support with orgId and platform roles
"""
from typing import Dict, Any, Optional
import base64
import json


class UserContext:
    """
    Represents the authenticated user from Cognito JWT token.
    
    Supports multi-tenant architecture with:
    - Platform roles: platform_admin, org_admin, technician, customer
    - Organization membership via orgId
    """
    def __init__(
        self,
        user_id: str,
        email: str,
        role: str = "customer",
        org_id: Optional[str] = None,
        given_name: Optional[str] = None,
        family_name: Optional[str] = None
    ):
        self.user_id = user_id  # Cognito sub (unique identifier)
        self.email = email
        self.role = role.lower()  # Normalize to lowercase
        self.org_id = org_id  # Organization ID for multi-tenancy
        self.given_name = given_name
        self.family_name = family_name
    
    @property
    def full_name(self) -> str:
        """Get user's full name if available."""
        if self.given_name and self.family_name:
            return f"{self.given_name} {self.family_name}"
        return self.email
    
    # ===========================================
    # Platform Role Checks
    # ===========================================
    
    @property
    def is_platform_admin(self) -> bool:
        """Platform admins can manage all organizations and users."""
        return self.role == "platform_admin"
    
    @property
    def is_org_admin(self) -> bool:
        """Org admins can manage their organization's settings and users."""
        return self.role == "org_admin"
    
    @property
    def is_technician(self) -> bool:
        """Technicians can work on tickets within their organization."""
        return self.role == "technician"
    
    @property
    def is_customer(self) -> bool:
        """Customers can create and view their own tickets."""
        return self.role == "customer"
    
    # ===========================================
    # Legacy Role Checks (for backward compatibility)
    # ===========================================
    
    @property
    def is_admin(self) -> bool:
        """Legacy: Maps to platform_admin or org_admin."""
        return self.is_platform_admin or self.is_org_admin
    
    @property
    def is_agent(self) -> bool:
        """Legacy: Maps to platform_admin, org_admin, or technician."""
        return self.is_platform_admin or self.is_org_admin or self.is_technician
    
    # ===========================================
    # Organization Access Checks
    # ===========================================
    
    def can_access_org(self, org_id: str) -> bool:
        """Check if user can access a specific organization's data."""
        # Platform admins can access all orgs
        if self.is_platform_admin:
            return True
        # Others can only access their own org
        return self.org_id == org_id
    
    def can_manage_org(self, org_id: str) -> bool:
        """Check if user can manage organization settings."""
        # Platform admins can manage all orgs
        if self.is_platform_admin:
            return True
        # Org admins can manage their own org
        return self.is_org_admin and self.org_id == org_id
    
    # ===========================================
    # Ticket Access Checks (Multi-tenant aware)
    # ===========================================
    
    def can_access_ticket(self, ticket: Dict[str, Any]) -> bool:
        """Check if user can access a specific ticket."""
        ticket_org_id = ticket.get('orgId')
        
        # Platform admins can access all tickets
        if self.is_platform_admin:
            return True
        
        # Must be in the same org to access ticket
        if ticket_org_id and self.org_id != ticket_org_id:
            return False
        
        # Org admins and technicians can access all tickets in their org
        if self.is_org_admin or self.is_technician:
            return True
        
        # Customers can only access their own tickets
        return ticket.get('createdBy') == self.user_id
    
    def can_update_ticket(self, ticket: Dict[str, Any]) -> bool:
        """Check if user can update a specific ticket."""
        ticket_org_id = ticket.get('orgId')
        
        # Platform admins can update all tickets
        if self.is_platform_admin:
            return True
        
        # Must be in the same org
        if ticket_org_id and self.org_id != ticket_org_id:
            return False
        
        # Org admins and technicians can update tickets in their org
        if self.is_org_admin or self.is_technician:
            return True
        
        # Customers can only update their own tickets
        return ticket.get('createdBy') == self.user_id
    
    def can_delete_ticket(self, ticket: Dict[str, Any], hard_delete: bool = False) -> bool:
        """Check if user can delete a specific ticket."""
        ticket_org_id = ticket.get('orgId')
        
        # Hard delete is platform admin only
        if hard_delete:
            return self.is_platform_admin
        
        # Platform admins can delete any ticket
        if self.is_platform_admin:
            return True
        
        # Must be in the same org
        if ticket_org_id and self.org_id != ticket_org_id:
            return False
        
        # Org admins can delete tickets in their org
        if self.is_org_admin:
            return True
        
        # Technicians can soft delete tickets they're working on
        if self.is_technician:
            return True
        
        # Customers can only delete their own tickets
        return ticket.get('createdBy') == self.user_id
    
    def can_assign_ticket(self, ticket: Dict[str, Any]) -> bool:
        """Check if user can assign a ticket to a technician."""
        ticket_org_id = ticket.get('orgId')
        
        # Platform admins can assign any ticket
        if self.is_platform_admin:
            return True
        
        # Must be in the same org
        if ticket_org_id and self.org_id != ticket_org_id:
            return False
        
        # Org admins and technicians can assign tickets in their org
        return self.is_org_admin or self.is_technician
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging/debugging."""
        return {
            'user_id': self.user_id,
            'email': self.email,
            'role': self.role,
            'org_id': self.org_id,
            'given_name': self.given_name,
            'family_name': self.family_name
        }


def extract_user_from_event(event: Dict[str, Any]) -> UserContext:
    """
    Extract authenticated user info from API Gateway event.
    
    The Cognito authorizer adds claims to requestContext.authorizer.claims
    
    Args:
        event: API Gateway Lambda proxy event
        
    Returns:
        UserContext with user information from JWT token
    """
    # Get claims from Cognito authorizer
    claims = (
        event.get('requestContext', {})
        .get('authorizer', {})
        .get('claims', {})
    )
    
    # If no claims (local testing or mock), return test user
    if not claims:
        print("WARNING: No Cognito claims found, using test user")
        return UserContext(
            user_id='test-user-123',
            email='test@example.com',
            role='customer',
            org_id='test-org-123',
            given_name='Test',
            family_name='User'
        )
    
    # Extract user info from claims
    user_id = claims.get('sub', 'unknown')
    email = claims.get('email', claims.get('cognito:username', 'unknown@example.com'))
    
    # Get role from custom attribute or default to customer
    # Cognito custom attributes are prefixed with 'custom:'
    role = claims.get('custom:role', 'customer')
    
    # Get organization ID from custom attribute
    org_id = claims.get('custom:orgId', None)
    
    # Get name attributes
    given_name = claims.get('given_name')
    family_name = claims.get('family_name')
    
    user = UserContext(
        user_id=user_id,
        email=email,
        role=role,
        org_id=org_id,
        given_name=given_name,
        family_name=family_name
    )
    
    print(f"Authenticated user: {user.email} (role: {user.role}, org: {user.org_id}, id: {user.user_id})")
    
    return user


def decode_jwt_payload(token: str) -> Dict[str, Any]:
    """
    Decode JWT token payload (for debugging/logging).
    Note: This does NOT verify the signature - that's done by API Gateway.
    
    Args:
        token: JWT token string
        
    Returns:
        Decoded payload as dictionary
    """
    try:
        # JWT has 3 parts: header.payload.signature
        parts = token.split('.')
        if len(parts) != 3:
            return {}
        
        # Decode payload (middle part)
        payload = parts[1]
        # Add padding if needed
        padding = 4 - len(payload) % 4
        if padding != 4:
            payload += '=' * padding
        
        decoded = base64.urlsafe_b64decode(payload)
        return json.loads(decoded)
    except Exception as e:
        print(f"Error decoding JWT: {e}")
        return {}