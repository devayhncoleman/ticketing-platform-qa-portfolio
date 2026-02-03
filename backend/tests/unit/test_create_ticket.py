"""
Unit tests for create_ticket Lambda function.
Updated for multi-tenant architecture with orgId support.
"""
import json
import pytest
from unittest.mock import patch, MagicMock
from src.functions.create_ticket import handler


class TestCreateTicket:
    """Test suite for create ticket functionality"""
    
    @patch('src.functions.create_ticket.tickets_table')
    @patch('src.functions.create_ticket.users_table')
    def test_create_ticket_with_valid_data_returns_201(self, mock_users_table, mock_tickets_table):
        """
        GIVEN valid ticket data in request body with authenticated user
        WHEN create_ticket handler is called
        THEN it should return 201 status code with ticket details including orgId
        """
        # Arrange
        mock_users_table.get_item.return_value = {}  # User doesn't exist yet
        mock_users_table.put_item.return_value = {}
        mock_tickets_table.put_item.return_value = {}
        
        event = {
            'body': json.dumps({
                'title': 'Login Issue',
                'description': 'Cannot access my account',
                'priority': 'HIGH'
            }),
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
        assert response['statusCode'] == 201
        assert 'ticketId' in body
        assert body['title'] == 'Login Issue'
        assert body['description'] == 'Cannot access my account'
        assert body['status'] == 'OPEN'
        assert body['priority'] == 'HIGH'
        assert body['orgId'] == 'org-456'
        assert 'createdAt' in body
    
    @patch('src.functions.create_ticket.tickets_table')
    @patch('src.functions.create_ticket.users_table')
    def test_create_ticket_without_title_returns_400(self, mock_users_table, mock_tickets_table):
        """
        GIVEN request without title
        WHEN create_ticket handler is called
        THEN it should return 400 with error message
        """
        # Arrange
        event = {
            'body': json.dumps({
                'description': 'Some description'
            }),
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
        assert 'Title is required' in body['error']
    
    @patch('src.functions.create_ticket.tickets_table')
    @patch('src.functions.create_ticket.users_table')
    def test_create_ticket_without_description_returns_400(self, mock_users_table, mock_tickets_table):
        """
        GIVEN request without description
        WHEN create_ticket handler is called
        THEN it should return 400 with error message
        """
        # Arrange
        event = {
            'body': json.dumps({
                'title': 'Some title'
            }),
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
        assert 'Description is required' in body['error']
    
    def test_create_ticket_with_invalid_json_returns_400(self):
        """
        GIVEN invalid JSON in request body
        WHEN create_ticket handler is called
        THEN it should return 400 with error message
        """
        # Arrange
        event = {
            'body': 'not valid json',
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
    
    @patch('src.functions.create_ticket.tickets_table')
    @patch('src.functions.create_ticket.users_table')
    def test_create_ticket_assigns_defaults(self, mock_users_table, mock_tickets_table):
        """
        GIVEN request without priority
        WHEN create_ticket handler is called
        THEN it should assign default values
        """
        # Arrange
        mock_users_table.get_item.return_value = {}
        mock_users_table.put_item.return_value = {}
        mock_tickets_table.put_item.return_value = {}
        
        event = {
            'body': json.dumps({
                'title': 'Test Ticket',
                'description': 'Test Description'
            }),
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
        assert response['statusCode'] == 201
        assert body['priority'] == 'MEDIUM'
        assert body['assignedTo'] is None
    
    @patch('src.functions.create_ticket.tickets_table')
    @patch('src.functions.create_ticket.users_table')
    def test_create_ticket_generates_unique_ticket_id(self, mock_users_table, mock_tickets_table):
        """
        GIVEN multiple ticket creation requests
        WHEN tickets are created
        THEN each should have a unique ticket ID
        """
        # Arrange
        mock_users_table.get_item.return_value = {}
        mock_users_table.put_item.return_value = {}
        mock_tickets_table.put_item.return_value = {}
        
        event = {
            'body': json.dumps({
                'title': 'Test Ticket',
                'description': 'Test Description'
            }),
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
        response1 = handler(event, {})
        response2 = handler(event, {})
        
        ticket1 = json.loads(response1['body'])
        ticket2 = json.loads(response2['body'])
        
        # Assert
        assert ticket1['ticketId'] != ticket2['ticketId']
    
    @patch('src.functions.create_ticket.tickets_table')
    @patch('src.functions.create_ticket.users_table')
    def test_create_ticket_with_invalid_priority_returns_400(self, mock_users_table, mock_tickets_table):
        """
        GIVEN request with invalid priority value
        WHEN create_ticket handler is called
        THEN it should return 400 with error message
        """
        # Arrange
        event = {
            'body': json.dumps({
                'title': 'Test Ticket',
                'description': 'Test Description',
                'priority': 'SUPER_URGENT'  # Invalid priority
            }),
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
        assert 'Invalid priority' in body['error']
    
    def test_create_ticket_without_org_returns_400(self):
        """
        GIVEN user without orgId
        WHEN create_ticket handler is called
        THEN it should return 400 requiring organization
        """
        # Arrange
        event = {
            'body': json.dumps({
                'title': 'Test Ticket',
                'description': 'Test Description'
            }),
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'sub': 'user-123',
                        'email': 'test@example.com',
                        'custom:role': 'customer'
                        # No custom:orgId
                    }
                }
            }
        }
        
        # Act
        response = handler(event, {})
        body = json.loads(response['body'])
        
        # Assert
        assert response['statusCode'] == 400
        assert 'Organization' in body['error']
    
    @patch('src.functions.create_ticket.tickets_table')
    @patch('src.functions.create_ticket.users_table')
    def test_platform_admin_can_create_ticket_in_any_org(self, mock_users_table, mock_tickets_table):
        """
        GIVEN platform admin specifying different orgId
        WHEN create_ticket handler is called
        THEN it should create ticket in specified org
        """
        # Arrange
        mock_users_table.get_item.return_value = {}
        mock_users_table.put_item.return_value = {}
        mock_tickets_table.put_item.return_value = {}
        
        event = {
            'body': json.dumps({
                'title': 'Test Ticket',
                'description': 'Test Description',
                'orgId': 'different-org-789'  # Different from admin's org
            }),
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
        body = json.loads(response['body'])
        
        # Assert
        assert response['statusCode'] == 201
        assert body['orgId'] == 'different-org-789'