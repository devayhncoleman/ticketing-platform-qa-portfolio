"""
Unit tests for get_ticket Lambda function.
Updated for multi-tenant architecture with orgId support.
"""
import json
import pytest
from unittest.mock import MagicMock, patch
from src.functions.get_ticket import handler


class TestGetTicket:
    """Test suite for get ticket functionality"""
    
    @patch('src.functions.get_ticket.tickets_table')
    def test_get_ticket_with_valid_id_returns_200(self, mock_table):
        """
        GIVEN a valid ticket ID
        WHEN get_ticket handler is called
        THEN it should return 200 with ticket data
        """
        # Arrange
        ticket_id = 'test-ticket-123'
        mock_ticket = {
            'ticketId': ticket_id,
            'title': 'Test Ticket',
            'status': 'OPEN',
            'createdBy': 'test-user-123',
            'orgId': 'org-456'
        }
        
        mock_table.get_item.return_value = {'Item': mock_ticket}
        
        event = {
            'pathParameters': {'ticketId': ticket_id},
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'sub': 'test-user-123',
                        'email': 'test@example.com',
                        'custom:role': 'platform_admin',
                        'custom:orgId': 'org-456'
                    }
                }
            }
        }
        
        # Act
        response = handler(event, {})
        body = json.loads(response['body'])
        
        # Assert
        assert response['statusCode'] == 200
        assert body['ticketId'] == ticket_id
        assert body['title'] == 'Test Ticket'
        mock_table.get_item.assert_called_once_with(Key={'ticketId': ticket_id})
    
    def test_get_ticket_without_id_returns_400(self):
        """
        GIVEN no ticket ID in path parameters
        WHEN get_ticket handler is called
        THEN it should return 400 with error message
        """
        # Arrange
        event = {
            'pathParameters': {},
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'sub': 'user-123',
                        'email': 'test@example.com',
                        'custom:role': 'customer',
                        'custom:orgId': 'org-456'
                    }
                }
            }
        }
        
        # Act
        response = handler(event, {})
        body = json.loads(response['body'])
        
        # Assert
        assert response['statusCode'] == 400
        assert 'error' in body
        assert 'Ticket ID is required' in body['error']
    
    @patch('src.functions.get_ticket.tickets_table')
    def test_get_ticket_not_found_returns_404(self, mock_table):
        """
        GIVEN a ticket ID that doesn't exist
        WHEN get_ticket handler is called
        THEN it should return 404
        """
        # Arrange
        mock_table.get_item.return_value = {}  # No 'Item' key
        
        event = {
            'pathParameters': {'ticketId': 'nonexistent-ticket'},
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'sub': 'test-user-123',
                        'email': 'test@example.com',
                        'custom:role': 'platform_admin',
                        'custom:orgId': 'org-456'
                    }
                }
            }
        }
        
        # Act
        response = handler(event, {})
        body = json.loads(response['body'])
        
        # Assert
        assert response['statusCode'] == 404
        assert 'error' in body
        assert 'Ticket not found' in body['error']
    
    @patch('src.functions.get_ticket.tickets_table')
    def test_customer_can_view_own_ticket(self, mock_table):
        """
        GIVEN a customer user
        WHEN they request their own ticket
        THEN they should be authorized to view it
        """
        # Arrange
        user_id = 'customer-123'
        org_id = 'org-456'
        mock_ticket = {
            'ticketId': 'ticket-1',
            'title': 'My Ticket',
            'createdBy': user_id,
            'orgId': org_id
        }
        
        mock_table.get_item.return_value = {'Item': mock_ticket}
        
        event = {
            'pathParameters': {'ticketId': 'ticket-1'},
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'sub': user_id,
                        'email': 'customer@example.com',
                        'custom:role': 'customer',
                        'custom:orgId': org_id
                    }
                }
            }
        }
        
        # Act
        response = handler(event, {})
        
        # Assert
        assert response['statusCode'] == 200
    
    @patch('src.functions.get_ticket.tickets_table')
    def test_customer_cannot_view_others_ticket(self, mock_table):
        """
        GIVEN a customer user
        WHEN they request another customer's ticket in the same org
        THEN they should receive 403 Forbidden
        """
        # Arrange
        org_id = 'org-456'
        mock_ticket = {
            'ticketId': 'ticket-1',
            'title': 'Someone Elses Ticket',
            'createdBy': 'other-customer-456',
            'orgId': org_id
        }
        
        mock_table.get_item.return_value = {'Item': mock_ticket}
        
        event = {
            'pathParameters': {'ticketId': 'ticket-1'},
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'sub': 'customer-123',
                        'email': 'customer@example.com',
                        'custom:role': 'customer',
                        'custom:orgId': org_id
                    }
                }
            }
        }
        
        # Act
        response = handler(event, {})
        body = json.loads(response['body'])
        
        # Assert
        assert response['statusCode'] == 403
        assert 'error' in body
    
    @patch('src.functions.get_ticket.tickets_table')
    def test_technician_can_view_ticket_in_same_org(self, mock_table):
        """
        GIVEN a technician user
        WHEN they request a ticket in their organization
        THEN they should be authorized to view it
        """
        # Arrange
        org_id = 'org-456'
        mock_ticket = {
            'ticketId': 'ticket-1',
            'title': 'Any Ticket',
            'createdBy': 'customer-999',
            'orgId': org_id
        }
        
        mock_table.get_item.return_value = {'Item': mock_ticket}
        
        event = {
            'pathParameters': {'ticketId': 'ticket-1'},
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'sub': 'tech-123',
                        'email': 'tech@example.com',
                        'custom:role': 'technician',
                        'custom:orgId': org_id
                    }
                }
            }
        }
        
        # Act
        response = handler(event, {})
        
        # Assert
        assert response['statusCode'] == 200
    
    @patch('src.functions.get_ticket.tickets_table')
    def test_technician_cannot_view_ticket_in_different_org(self, mock_table):
        """
        GIVEN a technician user
        WHEN they request a ticket from a different organization
        THEN they should receive 403 Forbidden
        """
        # Arrange
        mock_ticket = {
            'ticketId': 'ticket-1',
            'title': 'Other Org Ticket',
            'createdBy': 'customer-999',
            'orgId': 'different-org-789'
        }
        
        mock_table.get_item.return_value = {'Item': mock_ticket}
        
        event = {
            'pathParameters': {'ticketId': 'ticket-1'},
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'sub': 'tech-123',
                        'email': 'tech@example.com',
                        'custom:role': 'technician',
                        'custom:orgId': 'org-456'
                    }
                }
            }
        }
        
        # Act
        response = handler(event, {})
        body = json.loads(response['body'])
        
        # Assert
        assert response['statusCode'] == 403
        assert 'error' in body
    
    @patch('src.functions.get_ticket.tickets_table')
    def test_platform_admin_can_view_any_ticket(self, mock_table):
        """
        GIVEN a platform admin user
        WHEN they request any ticket from any org
        THEN they should be authorized to view it
        """
        # Arrange
        mock_ticket = {
            'ticketId': 'ticket-1',
            'title': 'Any Ticket',
            'createdBy': 'customer-999',
            'orgId': 'different-org-789'
        }
        
        mock_table.get_item.return_value = {'Item': mock_ticket}
        
        event = {
            'pathParameters': {'ticketId': 'ticket-1'},
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'sub': 'admin-123',
                        'email': 'admin@example.com',
                        'custom:role': 'platform_admin',
                        'custom:orgId': 'org-456'
                    }
                }
            }
        }
        
        # Act
        response = handler(event, {})
        
        # Assert
        assert response['statusCode'] == 200