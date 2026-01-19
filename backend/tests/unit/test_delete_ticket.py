"""
Unit tests for delete_ticket Lambda function.
Tests soft delete, hard delete, and authorization.
"""
import json
import pytest
from unittest.mock import patch
from botocore.exceptions import ClientError
from src.functions.delete_ticket import handler, is_authorized_to_delete


class TestDeleteTicket:
    """Test suite for delete ticket functionality"""
    
    @patch('src.functions.delete_ticket.table')
    def test_soft_delete_ticket_returns_204(self, mock_table):
        """
        GIVEN valid ticket ID
        WHEN delete_ticket handler is called
        THEN it should soft delete (close) and return 204
        """
        # Arrange
        ticket_id = 'test-123'
        existing_ticket = {'ticketId': ticket_id, 'status': 'OPEN', 'createdBy': 'user-1'}
        
        mock_table.get_item.return_value = {'Item': existing_ticket}
        mock_table.update_item.return_value = {}
        
        event = {
            'pathParameters': {'id': ticket_id},
            'queryStringParameters': None,
            'requestContext': {
                'authorizer': {'claims': {'sub': 'agent-1', 'custom:role': 'AGENT'}}
            }
        }
        
        # Act
        response = handler(event, {})
        
        # Assert
        assert response['statusCode'] == 204
        mock_table.update_item.assert_called_once()
        
        # Verify it updated status to CLOSED
        call_args = mock_table.update_item.call_args
        assert ':status' in call_args[1]['ExpressionAttributeValues']
        assert call_args[1]['ExpressionAttributeValues'][':status'] == 'CLOSED'
    
    @patch('src.functions.delete_ticket.table')
    def test_hard_delete_by_admin_returns_204(self, mock_table):
        """
        GIVEN admin user with hard=true parameter
        WHEN delete_ticket handler is called
        THEN it should permanently delete and return 204
        """
        # Arrange
        ticket_id = 'test-123'
        existing_ticket = {'ticketId': ticket_id, 'createdBy': 'user-1'}
        
        mock_table.get_item.return_value = {'Item': existing_ticket}
        mock_table.delete_item.return_value = {}
        
        event = {
            'pathParameters': {'id': ticket_id},
            'queryStringParameters': {'hard': 'true'},
            'requestContext': {
                'authorizer': {'claims': {'sub': 'admin-1', 'custom:role': 'ADMIN'}}
            }
        }
        
        # Act
        response = handler(event, {})
        
        # Assert
        assert response['statusCode'] == 204
        mock_table.delete_item.assert_called_once()
        mock_table.update_item.assert_not_called()
    
    @patch('src.functions.delete_ticket.table')
    def test_hard_delete_by_non_admin_returns_403(self, mock_table):
        """
        GIVEN non-admin user trying hard delete
        WHEN delete_ticket handler is called
        THEN it should return 403 Forbidden
        """
        # Arrange
        ticket_id = 'test-123'
        existing_ticket = {'ticketId': ticket_id, 'createdBy': 'agent-1'}
        
        mock_table.get_item.return_value = {'Item': existing_ticket}
        
        event = {
            'pathParameters': {'id': ticket_id},
            'queryStringParameters': {'hard': 'true'},
            'requestContext': {
                'authorizer': {'claims': {'sub': 'agent-1', 'custom:role': 'AGENT'}}
            }
        }
        
        # Act
        response = handler(event, {})
        body = json.loads(response['body'])
        
        # Assert
        assert response['statusCode'] == 403
        assert 'not authorized' in body['error'].lower()
    
    def test_delete_without_id_returns_400(self):
        """Test missing ticket ID"""
        event = {
            'pathParameters': {},
            'queryStringParameters': None,
            'requestContext': {}
        }
        
        response = handler(event, {})
        body = json.loads(response['body'])
        
        assert response['statusCode'] == 400
        assert 'Ticket ID is required' in body['error']
    
    @patch('src.functions.delete_ticket.table')
    def test_delete_nonexistent_ticket_returns_404(self, mock_table):
        """Test deleting ticket that doesn't exist"""
        mock_table.get_item.return_value = {}  # No Item
        
        event = {
            'pathParameters': {'id': 'nonexistent'},
            'queryStringParameters': None,
            'requestContext': {
                'authorizer': {'claims': {'sub': 'admin-1', 'custom:role': 'ADMIN'}}
            }
        }
        
        response = handler(event, {})
        assert response['statusCode'] == 404
    
    @patch('src.functions.delete_ticket.table')
    def test_customer_can_delete_own_ticket(self, mock_table):
        """Test customer can soft delete their own ticket"""
        customer_id = 'customer-1'
        ticket = {'ticketId': '123', 'createdBy': customer_id}
        
        mock_table.get_item.return_value = {'Item': ticket}
        mock_table.update_item.return_value = {}
        
        event = {
            'pathParameters': {'id': '123'},
            'queryStringParameters': None,
            'requestContext': {
                'authorizer': {'claims': {'sub': customer_id, 'custom:role': 'CUSTOMER'}}
            }
        }
        
        response = handler(event, {})
        assert response['statusCode'] == 204
    
    @patch('src.functions.delete_ticket.table')
    def test_customer_cannot_delete_others_ticket(self, mock_table):
        """Test customer cannot delete other customer's ticket"""
        ticket = {'ticketId': '123', 'createdBy': 'customer-2'}
        
        mock_table.get_item.return_value = {'Item': ticket}
        
        event = {
            'pathParameters': {'id': '123'},
            'queryStringParameters': None,
            'requestContext': {
                'authorizer': {'claims': {'sub': 'customer-1', 'custom:role': 'CUSTOMER'}}
            }
        }
        
        response = handler(event, {})
        body = json.loads(response['body'])
        
        assert response['statusCode'] == 403
        assert 'not authorized' in body['error'].lower()
    
    @patch('src.functions.delete_ticket.table')
    def test_agent_can_delete_any_ticket(self, mock_table):
        """Test agent can soft delete any ticket"""
        ticket = {'ticketId': '123', 'createdBy': 'customer-999'}
        
        mock_table.get_item.return_value = {'Item': ticket}
        mock_table.update_item.return_value = {}
        
        event = {
            'pathParameters': {'id': '123'},
            'queryStringParameters': None,
            'requestContext': {
                'authorizer': {'claims': {'sub': 'agent-1', 'custom:role': 'AGENT'}}
            }
        }
        
        response = handler(event, {})
        assert response['statusCode'] == 204


class TestIsAuthorizedToDelete:
    """Test authorization logic"""
    
    def test_admin_can_soft_delete(self):
        """Admin can soft delete any ticket"""
        ticket = {'createdBy': 'user-1'}
        assert is_authorized_to_delete(ticket, 'admin-1', 'ADMIN', False) is True
    
    def test_admin_can_hard_delete(self):
        """Admin can hard delete any ticket"""
        ticket = {'createdBy': 'user-1'}
        assert is_authorized_to_delete(ticket, 'admin-1', 'ADMIN', True) is True
    
    def test_agent_can_soft_delete(self):
        """Agent can soft delete any ticket"""
        ticket = {'createdBy': 'user-1'}
        assert is_authorized_to_delete(ticket, 'agent-1', 'AGENT', False) is True
    
    def test_agent_cannot_hard_delete(self):
        """Agent cannot hard delete"""
        ticket = {'createdBy': 'user-1'}
        assert is_authorized_to_delete(ticket, 'agent-1', 'AGENT', True) is False
    
    def test_customer_can_soft_delete_own(self):
        """Customer can soft delete their own ticket"""
        customer_id = 'customer-1'
        ticket = {'createdBy': customer_id}
        assert is_authorized_to_delete(ticket, customer_id, 'CUSTOMER', False) is True
    
    def test_customer_cannot_soft_delete_others(self):
        """Customer cannot soft delete other's ticket"""
        ticket = {'createdBy': 'customer-2'}
        assert is_authorized_to_delete(ticket, 'customer-1', 'CUSTOMER', False) is False
    
    def test_customer_cannot_hard_delete(self):
        """Customer cannot hard delete even their own ticket"""
        customer_id = 'customer-1'
        ticket = {'createdBy': customer_id}
        assert is_authorized_to_delete(ticket, customer_id, 'CUSTOMER', True) is False