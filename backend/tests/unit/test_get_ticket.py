"""
Unit tests for get_ticket Lambda function.
Following TDD approach - tests written alongside implementation.
"""
import json
import pytest
from unittest.mock import MagicMock, patch
from src.functions.get_ticket import handler, is_authorized


class TestGetTicket:
    """Test suite for get ticket functionality"""
    
    @patch('src.functions.get_ticket.table')
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
            'createdBy': 'test-user-123'
        }
        
        mock_table.get_item.return_value = {'Item': mock_ticket}
        
        event = {
            'pathParameters': {'id': ticket_id},
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'sub': 'test-user-123',
                        'custom:role': 'ADMIN'
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
            'requestContext': {}
        }
        
        # Act
        response = handler(event, {})
        body = json.loads(response['body'])
        
        # Assert
        assert response['statusCode'] == 400
        assert 'error' in body
        assert 'Ticket ID is required' in body['error']
    
    @patch('src.functions.get_ticket.table')
    def test_get_ticket_not_found_returns_404(self, mock_table):
        """
        GIVEN a ticket ID that doesn't exist
        WHEN get_ticket handler is called
        THEN it should return 404
        """
        # Arrange
        mock_table.get_item.return_value = {}  # No 'Item' key
        
        event = {
            'pathParameters': {'id': 'nonexistent-ticket'},
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'sub': 'test-user-123',
                        'custom:role': 'ADMIN'
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
    
    @patch('src.functions.get_ticket.table')
    def test_customer_can_view_own_ticket(self, mock_table):
        """
        GIVEN a customer user
        WHEN they request their own ticket
        THEN they should be authorized to view it
        """
        # Arrange
        user_id = 'customer-123'
        mock_ticket = {
            'ticketId': 'ticket-1',
            'title': 'My Ticket',
            'createdBy': user_id
        }
        
        mock_table.get_item.return_value = {'Item': mock_ticket}
        
        event = {
            'pathParameters': {'id': 'ticket-1'},
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'sub': user_id,
                        'custom:role': 'CUSTOMER'
                    }
                }
            }
        }
        
        # Act
        response = handler(event, {})
        
        # Assert
        assert response['statusCode'] == 200
    
    @patch('src.functions.get_ticket.table')
    def test_customer_cannot_view_others_ticket(self, mock_table):
        """
        GIVEN a customer user
        WHEN they request another customer's ticket
        THEN they should receive 403 Forbidden
        """
        # Arrange
        mock_ticket = {
            'ticketId': 'ticket-1',
            'title': 'Someone Elses Ticket',
            'createdBy': 'other-customer-456'
        }
        
        mock_table.get_item.return_value = {'Item': mock_ticket}
        
        event = {
            'pathParameters': {'id': 'ticket-1'},
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'sub': 'customer-123',
                        'custom:role': 'CUSTOMER'
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
        assert 'not authorized' in body['error'].lower()
    
    @patch('src.functions.get_ticket.table')
    def test_agent_can_view_any_ticket(self, mock_table):
        """
        GIVEN an agent user
        WHEN they request any ticket
        THEN they should be authorized to view it
        """
        # Arrange
        mock_ticket = {
            'ticketId': 'ticket-1',
            'title': 'Any Ticket',
            'createdBy': 'customer-999'
        }
        
        mock_table.get_item.return_value = {'Item': mock_ticket}
        
        event = {
            'pathParameters': {'id': 'ticket-1'},
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'sub': 'agent-123',
                        'custom:role': 'AGENT'
                    }
                }
            }
        }
        
        # Act
        response = handler(event, {})
        
        # Assert
        assert response['statusCode'] == 200
    
    @patch('src.functions.get_ticket.table')
    def test_admin_can_view_any_ticket(self, mock_table):
        """
        GIVEN an admin user
        WHEN they request any ticket
        THEN they should be authorized to view it
        """
        # Arrange
        mock_ticket = {
            'ticketId': 'ticket-1',
            'title': 'Any Ticket',
            'createdBy': 'customer-999'
        }
        
        mock_table.get_item.return_value = {'Item': mock_ticket}
        
        event = {
            'pathParameters': {'id': 'ticket-1'},
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'sub': 'admin-123',
                        'custom:role': 'ADMIN'
                    }
                }
            }
        }
        
        # Act
        response = handler(event, {})
        
        # Assert
        assert response['statusCode'] == 200


class TestIsAuthorized:
    """Test suite for authorization logic"""
    
    def test_admin_authorized_for_any_ticket(self):
        """Admins can view all tickets"""
        ticket = {'createdBy': 'user-123'}
        assert is_authorized(ticket, 'admin-456', 'ADMIN') is True
    
    def test_agent_authorized_for_any_ticket(self):
        """Agents can view all tickets"""
        ticket = {'createdBy': 'user-123'}
        assert is_authorized(ticket, 'agent-456', 'AGENT') is True
    
    def test_customer_authorized_for_own_ticket(self):
        """Customers can view their own tickets"""
        user_id = 'customer-123'
        ticket = {'createdBy': user_id}
        assert is_authorized(ticket, user_id, 'CUSTOMER') is True
    
    def test_customer_not_authorized_for_others_ticket(self):
        """Customers cannot view other customers' tickets"""
        ticket = {'createdBy': 'customer-456'}
        assert is_authorized(ticket, 'customer-123', 'CUSTOMER') is False
    
    def test_unknown_role_not_authorized(self):
        """Unknown roles are denied by default"""
        ticket = {'createdBy': 'user-123'}
        assert is_authorized(ticket, 'user-123', 'UNKNOWN_ROLE') is False