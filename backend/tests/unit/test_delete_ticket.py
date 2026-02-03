"""
Unit tests for delete_ticket Lambda function.
Updated for multi-tenant architecture with orgId access control.
"""
import json
import pytest
from unittest.mock import patch
from botocore.exceptions import ClientError
from src.functions.delete_ticket import handler


class TestDeleteTicket:
    """Test suite for delete ticket functionality"""
    
    @patch('src.functions.delete_ticket.tickets_table')
    def test_soft_delete_ticket_returns_200(self, mock_table):
        """
        GIVEN valid ticket ID
        WHEN delete_ticket handler is called by authorized user
        THEN it should soft delete and return 200
        """
        # Arrange
        ticket_id = 'test-123'
        org_id = 'org-456'
        existing_ticket = {
            'ticketId': ticket_id,
            'status': 'OPEN',
            'createdBy': 'user-1',
            'orgId': org_id
        }
        
        mock_table.get_item.return_value = {'Item': existing_ticket}
        mock_table.update_item.return_value = {
            'Attributes': {**existing_ticket, 'status': 'DELETED'}
        }
        
        event = {
            'pathParameters': {'ticketId': ticket_id},
            'queryStringParameters': None,
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'sub': 'tech-1',
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
        mock_table.update_item.assert_called_once()
    
    @patch('src.functions.delete_ticket.tickets_table')
    def test_hard_delete_by_platform_admin_returns_200(self, mock_table):
        """
        GIVEN platform admin user with hard=true parameter
        WHEN delete_ticket handler is called
        THEN it should permanently delete and return 200
        """
        # Arrange
        ticket_id = 'test-123'
        existing_ticket = {
            'ticketId': ticket_id,
            'createdBy': 'user-1',
            'orgId': 'org-456'
        }
        
        mock_table.get_item.return_value = {'Item': existing_ticket}
        mock_table.delete_item.return_value = {}
        
        event = {
            'pathParameters': {'ticketId': ticket_id},
            'queryStringParameters': {'hard': 'true'},
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'sub': 'admin-1',
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
        mock_table.delete_item.assert_called_once()
    
    @patch('src.functions.delete_ticket.tickets_table')
    def test_hard_delete_by_non_platform_admin_returns_403(self, mock_table):
        """
        GIVEN non-platform-admin user trying hard delete
        WHEN delete_ticket handler is called
        THEN it should return 403 Forbidden
        """
        # Arrange
        ticket_id = 'test-123'
        org_id = 'org-456'
        existing_ticket = {
            'ticketId': ticket_id,
            'createdBy': 'tech-1',
            'orgId': org_id
        }
        
        mock_table.get_item.return_value = {'Item': existing_ticket}
        
        event = {
            'pathParameters': {'ticketId': ticket_id},
            'queryStringParameters': {'hard': 'true'},
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'sub': 'tech-1',
                        'email': 'tech@example.com',
                        'custom:role': 'technician',
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
        assert 'platform administrator' in body['error'].lower()
    
    def test_delete_without_id_returns_400(self):
        """Test missing ticket ID"""
        event = {
            'pathParameters': {},
            'queryStringParameters': None,
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'sub': 'user-1',
                        'email': 'user@example.com',
                        'custom:role': 'customer',
                        'custom:orgId': 'org-456'
                    }
                }
            }
        }
        
        response = handler(event, {})
        body = json.loads(response['body'])
        
        assert response['statusCode'] == 400
        assert 'Ticket ID is required' in body['error']
    
    @patch('src.functions.delete_ticket.tickets_table')
    def test_delete_nonexistent_ticket_returns_404(self, mock_table):
        """Test deleting ticket that doesn't exist"""
        mock_table.get_item.return_value = {}  # No Item
        
        event = {
            'pathParameters': {'ticketId': 'nonexistent'},
            'queryStringParameters': None,
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'sub': 'admin-1',
                        'email': 'admin@example.com',
                        'custom:role': 'platform_admin',
                        'custom:orgId': 'org-456'
                    }
                }
            }
        }
        
        response = handler(event, {})
        assert response['statusCode'] == 404
    
    @patch('src.functions.delete_ticket.tickets_table')
    def test_customer_can_delete_own_ticket(self, mock_table):
        """Test customer can soft delete their own ticket"""
        customer_id = 'customer-1'
        org_id = 'org-456'
        ticket = {
            'ticketId': '123',
            'createdBy': customer_id,
            'orgId': org_id
        }
        
        mock_table.get_item.return_value = {'Item': ticket}
        mock_table.update_item.return_value = {
            'Attributes': {**ticket, 'status': 'DELETED'}
        }
        
        event = {
            'pathParameters': {'ticketId': '123'},
            'queryStringParameters': None,
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'sub': customer_id,
                        'email': 'customer@example.com',
                        'custom:role': 'customer',
                        'custom:orgId': org_id
                    }
                }
            }
        }
        
        response = handler(event, {})
        assert response['statusCode'] == 200
    
    @patch('src.functions.delete_ticket.tickets_table')
    def test_customer_cannot_delete_others_ticket(self, mock_table):
        """Test customer cannot delete other customer's ticket"""
        org_id = 'org-456'
        ticket = {
            'ticketId': '123',
            'createdBy': 'customer-2',
            'orgId': org_id
        }
        
        mock_table.get_item.return_value = {'Item': ticket}
        
        event = {
            'pathParameters': {'ticketId': '123'},
            'queryStringParameters': None,
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'sub': 'customer-1',
                        'email': 'customer@example.com',
                        'custom:role': 'customer',
                        'custom:orgId': org_id
                    }
                }
            }
        }
        
        response = handler(event, {})
        body = json.loads(response['body'])
        
        assert response['statusCode'] == 403
    
    @patch('src.functions.delete_ticket.tickets_table')
    def test_technician_can_delete_ticket_in_same_org(self, mock_table):
        """Test technician can soft delete any ticket in their org"""
        org_id = 'org-456'
        ticket = {
            'ticketId': '123',
            'createdBy': 'customer-999',
            'orgId': org_id
        }
        
        mock_table.get_item.return_value = {'Item': ticket}
        mock_table.update_item.return_value = {
            'Attributes': {**ticket, 'status': 'DELETED'}
        }
        
        event = {
            'pathParameters': {'ticketId': '123'},
            'queryStringParameters': None,
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'sub': 'tech-1',
                        'email': 'tech@example.com',
                        'custom:role': 'technician',
                        'custom:orgId': org_id
                    }
                }
            }
        }
        
        response = handler(event, {})
        assert response['statusCode'] == 200
    
    @patch('src.functions.delete_ticket.tickets_table')
    def test_technician_cannot_delete_ticket_in_different_org(self, mock_table):
        """Test technician cannot delete ticket from different org"""
        ticket = {
            'ticketId': '123',
            'createdBy': 'customer-999',
            'orgId': 'different-org'
        }
        
        mock_table.get_item.return_value = {'Item': ticket}
        
        event = {
            'pathParameters': {'ticketId': '123'},
            'queryStringParameters': None,
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'sub': 'tech-1',
                        'email': 'tech@example.com',
                        'custom:role': 'technician',
                        'custom:orgId': 'org-456'
                    }
                }
            }
        }
        
        response = handler(event, {})
        body = json.loads(response['body'])
        
        assert response['statusCode'] == 403
    
    @patch('src.functions.delete_ticket.tickets_table')
    def test_platform_admin_can_delete_any_ticket(self, mock_table):
        """Test platform admin can delete tickets from any org"""
        ticket = {
            'ticketId': '123',
            'createdBy': 'customer-999',
            'orgId': 'different-org'
        }
        
        mock_table.get_item.return_value = {'Item': ticket}
        mock_table.update_item.return_value = {
            'Attributes': {**ticket, 'status': 'DELETED'}
        }
        
        event = {
            'pathParameters': {'ticketId': '123'},
            'queryStringParameters': None,
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'sub': 'admin-1',
                        'email': 'admin@example.com',
                        'custom:role': 'platform_admin',
                        'custom:orgId': 'org-456'
                    }
                }
            }
        }
        
        response = handler(event, {})
        assert response['statusCode'] == 200