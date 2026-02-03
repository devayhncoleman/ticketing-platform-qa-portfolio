"""
Unit tests for update_ticket Lambda function.
Updated for multi-tenant architecture with orgId access control.
"""
import json
import pytest
from unittest.mock import patch, MagicMock
from botocore.exceptions import ClientError
from src.functions.update_ticket import handler


class TestUpdateTicket:
    """Test suite for update ticket functionality"""
    
    @patch('src.functions.update_ticket.tickets_table')
    def test_update_ticket_status_returns_200(self, mock_table):
        """
        GIVEN valid ticket ID and status update
        WHEN update_ticket handler is called by authorized user
        THEN it should update and return 200
        """
        # Arrange
        ticket_id = 'test-ticket-123'
        org_id = 'org-456'
        existing_ticket = {
            'ticketId': ticket_id,
            'status': 'OPEN',
            'createdBy': 'user-123',
            'orgId': org_id
        }
        
        updated_ticket = {**existing_ticket, 'status': 'IN_PROGRESS'}
        
        mock_table.get_item.return_value = {'Item': existing_ticket}
        mock_table.update_item.return_value = {'Attributes': updated_ticket}
        
        event = {
            'pathParameters': {'ticketId': ticket_id},
            'body': json.dumps({'status': 'IN_PROGRESS'}),
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
        body = json.loads(response['body'])
        
        # Assert
        assert response['statusCode'] == 200
        assert body['status'] == 'IN_PROGRESS'
        mock_table.update_item.assert_called_once()
    
    @patch('src.functions.update_ticket.tickets_table')
    def test_update_ticket_priority_by_owner_returns_200(self, mock_table):
        """Test customer updating their own ticket's priority"""
        ticket_id = 'test-123'
        user_id = 'customer-123'
        org_id = 'org-456'
        existing = {
            'ticketId': ticket_id,
            'createdBy': user_id,
            'priority': 'LOW',
            'orgId': org_id
        }
        updated = {**existing, 'priority': 'HIGH'}
        
        mock_table.get_item.return_value = {'Item': existing}
        mock_table.update_item.return_value = {'Attributes': updated}
        
        event = {
            'pathParameters': {'ticketId': ticket_id},
            'body': json.dumps({'priority': 'HIGH'}),
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
        
        response = handler(event, {})
        assert response['statusCode'] == 200
    
    def test_update_ticket_without_id_returns_400(self):
        """Test missing ticket ID"""
        event = {
            'pathParameters': {},
            'body': json.dumps({'status': 'OPEN'}),
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'sub': 'user-123',
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
    
    @patch('src.functions.update_ticket.tickets_table')
    def test_update_ticket_without_body_returns_400(self, mock_table):
        """Test missing request body"""
        existing = {'ticketId': '123', 'createdBy': 'user-1', 'orgId': 'org-456'}
        mock_table.get_item.return_value = {'Item': existing}
        
        event = {
            'pathParameters': {'ticketId': 'test-123'},
            'body': json.dumps({}),
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'sub': 'user-1',
                        'email': 'user@example.com',
                        'custom:role': 'platform_admin',
                        'custom:orgId': 'org-456'
                    }
                }
            }
        }
        
        response = handler(event, {})
        body = json.loads(response['body'])
        
        assert response['statusCode'] == 400
    
    @patch('src.functions.update_ticket.tickets_table')
    def test_update_nonexistent_ticket_returns_404(self, mock_table):
        """Test updating ticket that doesn't exist"""
        mock_table.get_item.return_value = {}  # No Item
        
        event = {
            'pathParameters': {'ticketId': 'nonexistent'},
            'body': json.dumps({'status': 'OPEN'}),
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'sub': 'user-1',
                        'email': 'user@example.com',
                        'custom:role': 'platform_admin',
                        'custom:orgId': 'org-456'
                    }
                }
            }
        }
        
        response = handler(event, {})
        assert response['statusCode'] == 404
    
    @patch('src.functions.update_ticket.tickets_table')
    def test_customer_cannot_update_others_ticket(self, mock_table):
        """Test customer authorization - cannot update other's tickets"""
        org_id = 'org-456'
        existing = {
            'ticketId': '123',
            'createdBy': 'other-customer',
            'orgId': org_id
        }
        mock_table.get_item.return_value = {'Item': existing}
        
        event = {
            'pathParameters': {'ticketId': '123'},
            'body': json.dumps({'title': 'Hacked Title'}),
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
    
    @patch('src.functions.update_ticket.tickets_table')
    def test_technician_can_update_ticket_in_same_org(self, mock_table):
        """Test technician can update any ticket in their org"""
        org_id = 'org-456'
        existing = {
            'ticketId': '123',
            'createdBy': 'customer-999',
            'orgId': org_id
        }
        updated = {**existing, 'status': 'IN_PROGRESS'}
        
        mock_table.get_item.return_value = {'Item': existing}
        mock_table.update_item.return_value = {'Attributes': updated}
        
        event = {
            'pathParameters': {'ticketId': '123'},
            'body': json.dumps({'status': 'IN_PROGRESS'}),
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
    
    @patch('src.functions.update_ticket.tickets_table')
    def test_technician_cannot_update_ticket_in_different_org(self, mock_table):
        """Test technician cannot update ticket from different org"""
        existing = {
            'ticketId': '123',
            'createdBy': 'customer-999',
            'orgId': 'different-org'
        }
        
        mock_table.get_item.return_value = {'Item': existing}
        
        event = {
            'pathParameters': {'ticketId': '123'},
            'body': json.dumps({'status': 'IN_PROGRESS'}),
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
    
    @patch('src.functions.update_ticket.tickets_table')
    def test_platform_admin_can_update_any_ticket(self, mock_table):
        """Test platform admin can update tickets from any org"""
        existing = {
            'ticketId': '123',
            'createdBy': 'customer-999',
            'orgId': 'different-org'
        }
        updated = {**existing, 'status': 'IN_PROGRESS'}
        
        mock_table.get_item.return_value = {'Item': existing}
        mock_table.update_item.return_value = {'Attributes': updated}
        
        event = {
            'pathParameters': {'ticketId': '123'},
            'body': json.dumps({'status': 'IN_PROGRESS'}),
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