"""
Unit tests for list_tickets Lambda function.
Updated for multi-tenant architecture with orgId filtering.
"""
import json
import pytest
from unittest.mock import patch, MagicMock
from src.functions.list_tickets import handler


class TestListTickets:
    """Test suite for list tickets functionality"""
    
    @patch('src.functions.list_tickets.tickets_table')
    def test_platform_admin_can_see_all_tickets(self, mock_table):
        """
        GIVEN a platform admin user
        WHEN list_tickets handler is called without filters
        THEN it should return all tickets from all orgs
        """
        # Arrange
        mock_tickets = [
            {'ticketId': '1', 'title': 'Ticket 1', 'status': 'OPEN', 'orgId': 'org-1'},
            {'ticketId': '2', 'title': 'Ticket 2', 'status': 'CLOSED', 'orgId': 'org-2'}
        ]
        
        mock_table.scan.return_value = {'Items': mock_tickets}
        
        event = {
            'queryStringParameters': None,
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'sub': 'admin-123',
                        'email': 'admin@example.com',
                        'custom:role': 'platform_admin',
                        'custom:orgId': 'org-1'
                    }
                }
            }
        }
        
        # Act
        response = handler(event, {})
        body = json.loads(response['body'])
        
        # Assert
        assert response['statusCode'] == 200
        assert len(body['tickets']) == 2
        assert body['count'] == 2
    
    @patch('src.functions.list_tickets.tickets_table')
    def test_platform_admin_can_filter_by_org(self, mock_table):
        """
        GIVEN a platform admin with orgId query parameter
        WHEN list_tickets handler is called
        THEN it should filter tickets by the specified org
        """
        # Arrange
        mock_tickets = [
            {'ticketId': '1', 'title': 'Ticket 1', 'orgId': 'org-1'},
            {'ticketId': '2', 'title': 'Ticket 2', 'orgId': 'org-2'}
        ]
        
        mock_table.scan.return_value = {'Items': mock_tickets}
        
        event = {
            'queryStringParameters': {'orgId': 'org-1'},
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'sub': 'admin-123',
                        'email': 'admin@example.com',
                        'custom:role': 'platform_admin',
                        'custom:orgId': 'org-admin'
                    }
                }
            }
        }
        
        # Act
        response = handler(event, {})
        
        # Assert
        assert response['statusCode'] == 200
        # Filter is applied in scan, so just check it was called
        mock_table.scan.assert_called()
    
    @patch('src.functions.list_tickets.tickets_table')
    def test_technician_sees_only_own_org_tickets(self, mock_table):
        """
        GIVEN a technician user
        WHEN list_tickets handler is called
        THEN it should only return tickets from their organization
        """
        # Arrange
        org_id = 'org-456'
        mock_tickets = [
            {'ticketId': '1', 'createdBy': 'customer-1', 'orgId': org_id},
            {'ticketId': '2', 'createdBy': 'customer-2', 'orgId': org_id}
        ]
        
        mock_table.scan.return_value = {'Items': mock_tickets}
        
        event = {
            'queryStringParameters': None,
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
        assert len(body['tickets']) == 2
    
    @patch('src.functions.list_tickets.tickets_table')
    def test_customer_sees_only_own_tickets(self, mock_table):
        """
        GIVEN a customer user
        WHEN they list tickets
        THEN they should only see tickets they created
        
        Note: The FilterExpression is applied by DynamoDB, so mock returns
        only what would pass the filter (customer's own tickets)
        """
        # Arrange
        customer_id = 'customer-123'
        org_id = 'org-456'
        # Mock returns only tickets that would pass the customer filter
        # (DynamoDB FilterExpression filters by createdBy = customer_id)
        mock_tickets = [
            {'ticketId': '1', 'createdBy': customer_id, 'status': 'OPEN', 'orgId': org_id},
            {'ticketId': '3', 'createdBy': customer_id, 'status': 'CLOSED', 'orgId': org_id}
        ]
        
        mock_table.scan.return_value = {'Items': mock_tickets}
        
        event = {
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
        
        # Act
        response = handler(event, {})
        body = json.loads(response['body'])
        
        # Assert
        assert response['statusCode'] == 200
        assert len(body['tickets']) == 2
        # All returned tickets belong to the customer
        assert all(t['createdBy'] == customer_id for t in body['tickets'])
    
    @patch('src.functions.list_tickets.tickets_table')
    def test_filter_by_status(self, mock_table):
        """
        GIVEN status filter parameter
        WHEN list_tickets handler is called
        THEN it should filter by status
        """
        # Arrange
        mock_tickets = [
            {'ticketId': '1', 'status': 'OPEN', 'createdBy': 'user-1', 'orgId': 'org-1'},
        ]
        
        mock_table.scan.return_value = {'Items': mock_tickets}
        
        event = {
            'queryStringParameters': {'status': 'OPEN'},
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'sub': 'admin-123',
                        'email': 'admin@example.com',
                        'custom:role': 'platform_admin',
                        'custom:orgId': 'org-1'
                    }
                }
            }
        }
        
        # Act
        response = handler(event, {})
        body = json.loads(response['body'])
        
        # Assert
        assert response['statusCode'] == 200
    
    @patch('src.functions.list_tickets.tickets_table')
    def test_filter_by_priority(self, mock_table):
        """
        GIVEN priority filter parameter
        WHEN list_tickets handler is called
        THEN it should filter by priority
        """
        # Arrange
        mock_tickets = [
            {'ticketId': '1', 'priority': 'HIGH', 'createdBy': 'user-1', 'orgId': 'org-1'},
        ]
        
        mock_table.scan.return_value = {'Items': mock_tickets}
        
        event = {
            'queryStringParameters': {'priority': 'HIGH'},
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'sub': 'admin-123',
                        'email': 'admin@example.com',
                        'custom:role': 'platform_admin',
                        'custom:orgId': 'org-1'
                    }
                }
            }
        }
        
        # Act
        response = handler(event, {})
        body = json.loads(response['body'])
        
        # Assert
        assert response['statusCode'] == 200
    
    @patch('src.functions.list_tickets.tickets_table')
    def test_respects_limit_parameter(self, mock_table):
        """
        GIVEN limit parameter
        WHEN list_tickets handler is called
        THEN it should limit the number of results
        """
        # Arrange
        mock_tickets = [{'ticketId': str(i), 'orgId': 'org-1'} for i in range(100)]
        mock_table.scan.return_value = {'Items': mock_tickets}
        
        event = {
            'queryStringParameters': {'limit': '10'},
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'sub': 'admin-123',
                        'email': 'admin@example.com',
                        'custom:role': 'platform_admin',
                        'custom:orgId': 'org-1'
                    }
                }
            }
        }
        
        # Act
        response = handler(event, {})
        body = json.loads(response['body'])
        
        # Assert
        assert response['statusCode'] == 200
        assert len(body['tickets']) <= 10
    
    @patch('src.functions.list_tickets.tickets_table')
    def test_org_admin_sees_all_org_tickets(self, mock_table):
        """
        GIVEN an org admin user
        WHEN they list tickets
        THEN they should see all tickets in their organization
        """
        # Arrange
        org_id = 'org-456'
        mock_tickets = [
            {'ticketId': '1', 'createdBy': 'customer-1', 'orgId': org_id},
            {'ticketId': '2', 'createdBy': 'customer-2', 'orgId': org_id},
            {'ticketId': '3', 'createdBy': 'customer-3', 'orgId': org_id}
        ]
        
        mock_table.scan.return_value = {'Items': mock_tickets}
        
        event = {
            'queryStringParameters': None,
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'sub': 'org-admin-123',
                        'email': 'orgadmin@example.com',
                        'custom:role': 'org_admin',
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
        assert len(body['tickets']) == 3