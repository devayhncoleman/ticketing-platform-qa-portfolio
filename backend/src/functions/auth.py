"""
Authentication utilities for extracting user info from Cognito JWT tokens.
Used by all Lambda functions to get authenticated user context.
"""
from typing import Dict, Any, Optional
import base64
import json


class UserContext:
    """
    Represents the authenticated user from Cognito JWT token.
    """
    def __init__(
        self,
        user_id: str,
        email: str,
        role: str = "CUSTOMER",
        given_name: Optional[str] = None,
        family_name: Optional[str] = None
    ):
        self.user_id = user_id  # Cognito sub (unique identifier)
        self.email = email
        self.role = role.upper()
        self.given_name = given_name
        self.family_name = family_name
    
    @property
    def full_name(self) -> str:
        """Get user's full name if available."""
        if self.given_name and self.family_name:
            return f"{self.given_name} {self.family_name}"
        return self.email
    
    @property
    def is_admin(self) -> bool:
        return self.role == "ADMIN"
    
    @property
    def is_agent(self) -> bool:
        return self.role in ("ADMIN", "AGENT")
    
    @property
    def is_customer(self) -> bool:
        return self.role == "CUSTOMER"
    
    def can_access_ticket(self, ticket: Dict[str, Any]) -> bool:
        """Check if user can access a specific ticket."""
        # Admins and agents can access all tickets
        if self.is_agent:
            return True
        # Customers can only access their own tickets
        return ticket.get('createdBy') == self.user_id
    
    def can_update_ticket(self, ticket: Dict[str, Any]) -> bool:
        """Check if user can update a specific ticket."""
        # Admins and agents can update all tickets
        if self.is_agent:
            return True
        # Customers can only update their own tickets
        return ticket.get('createdBy') == self.user_id
    
    def can_delete_ticket(self, ticket: Dict[str, Any], hard_delete: bool = False) -> bool:
        """Check if user can delete a specific ticket."""
        # Hard delete is admin only
        if hard_delete:
            return self.is_admin
        # Soft delete: Admins and agents can delete any ticket
        if self.is_agent:
            return True
        # Customers can only delete their own tickets
        return ticket.get('createdBy') == self.user_id
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging/debugging."""
        return {
            'user_id': self.user_id,
            'email': self.email,
            'role': self.role,
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
            role='CUSTOMER',
            given_name='Test',
            family_name='User'
        )
    
    # Extract user info from claims
    user_id = claims.get('sub', 'unknown')
    email = claims.get('email', claims.get('cognito:username', 'unknown@example.com'))
    
    # Get role from custom attribute or default to CUSTOMER
    # Cognito custom attributes are prefixed with 'custom:'
    role = claims.get('custom:role', 'CUSTOMER')
    
    # Get name attributes
    given_name = claims.get('given_name')
    family_name = claims.get('family_name')
    
    user = UserContext(
        user_id=user_id,
        email=email,
        role=role,
        given_name=given_name,
        family_name=family_name
    )
    
    print(f"Authenticated user: {user.email} (role: {user.role}, id: {user.user_id})")
    
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