"""
Unit tests for list_tickets Lambda function.
Tests GSI queries, pagination, and role-based filtering.
"""
import json
import pytest
from unittest.mock import patch, MagicMock
from src.functions.list_tickets import (
    handler, 
    filter_tickets_by_role,
    encode_cursor,
    decode_cursor
)


class TestListTickets:
    """Test suite for list tickets functionality"""
    
    @patch('src.functions.list_tickets.table')
    def test_list_tickets_without_filters_returns_all(self, mock_table):
        """
        GIVEN no filter parameters
        WHEN list_tickets handler is called by an admin
        THEN it should return all tickets via scan
        """
        # Arrange
        mock_tickets = [
            {'ticketId': '1', 'title': 'Ticket 1', 'status': 'OPEN'},
            {'ticketId': '2', 'title': 'Ticket 2', 'status': 'CLOSED'}
        ]
        
        mock_table.scan.return_value = {'Items': mock_tickets}
        
        event = {
            'queryStringParameters': None,
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
        body = json.loads(response['body'])
        
        # Assert
        assert response['statusCode'] == 200
        assert len(body['tickets']) == 2
        assert body['count'] == 2
        mock_table.scan.assert_called_once()
    
    @patch('src.functions.list_tickets.table')
    def test_list_tickets_filter_by_status_uses_gsi(self, mock_table):
        """
        GIVEN status filter parameter
        WHEN list_tickets handler is called
        THEN it should query StatusIndex GSI
        """
        # Arrange
        mock_tickets = [
            {'ticketId': '1', 'status': 'OPEN', 'createdBy': 'user-1'},
            {'ticketId': '2', 'status': 'OPEN', 'createdBy': 'user-2'}
        ]
        
        mock_table.query.return_value = {'Items': mock_tickets}
        
        event = {
            'queryStringParameters': {'status': 'OPEN'},
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
        body = json.loads(response['body'])
        
        # Assert
        assert response['statusCode'] == 200
        assert len(body['tickets']) == 2
        
        # Verify GSI query was called correctly
        call_args = mock_table.query.call_args
        assert call_args[1]['IndexName'] == 'StatusIndex'
        assert call_args[1]['KeyConditionExpression'] == '#status = :status'
    
    @patch('src.functions.list_tickets.table')
    def test_list_tickets_filter_by_assigned_to_uses_gsi(self, mock_table):
        """
        GIVEN assignedTo filter parameter
        WHEN list_tickets handler is called
        THEN it should query AssignedToIndex GSI
        """
        # Arrange
        agent_id = 'agent-123'
        mock_tickets = [
            {'ticketId': '1', 'assignedTo': agent_id, 'status': 'IN_PROGRESS'},
            {'ticketId': '2', 'assignedTo': agent_id, 'status': 'OPEN'}
        ]
        
        mock_table.query.return_value = {'Items': mock_tickets}
        
        event = {
            'queryStringParameters': {'assignedTo': agent_id},
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'sub': agent_id,
                        'custom:role': 'AGENT'
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
        
        # Verify GSI query
        call_args = mock_table.query.call_args
        assert call_args[1]['IndexName'] == 'AssignedToIndex'
    
    @patch('src.functions.list_tickets.table')
    def test_list_tickets_respects_limit_parameter(self, mock_table):
        """
        GIVEN limit parameter
        WHEN list_tickets handler is called
        THEN it should limit the number of results
        """
        # Arrange
        mock_table.scan.return_value = {'Items': []}
        
        event = {
            'queryStringParameters': {'limit': '10'},
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'sub': 'user-123',
                        'custom:role': 'ADMIN'
                    }
                }
            }
        }
        
        # Act
        response = handler(event, {})
        
        # Assert
        assert response['statusCode'] == 200
        call_args = mock_table.scan.call_args
        assert call_args[1]['Limit'] == 10
    
    @patch('src.functions.list_tickets.table')
    def test_list_tickets_rejects_excessive_limit(self, mock_table):
        """
        GIVEN limit > 100
        WHEN list_tickets handler is called
        THEN it should return 400 error
        """
        # Arrange
        event = {
            'queryStringParameters': {'limit': '150'},
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'sub': 'user-123',
                        'custom:role': 'ADMIN'
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
        assert 'cannot exceed 100' in body['error']
    
    @patch('src.functions.list_tickets.table')
    def test_list_tickets_includes_pagination_cursor(self, mock_table):
        """
        GIVEN more results available
        WHEN list_tickets handler is called
        THEN it should include nextCursor for pagination
        """
        # Arrange
        last_key = {'ticketId': 'ticket-50', 'createdAt': '2026-01-19T10:00:00Z'}
        mock_table.scan.return_value = {
            'Items': [{'ticketId': '1'}],
            'LastEvaluatedKey': last_key
        }
        
        event = {
            'queryStringParameters': None,
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'sub': 'user-123',
                        'custom:role': 'ADMIN'
                    }
                }
            }
        }
        
        # Act
        response = handler(event, {})
        body = json.loads(response['body'])
        
        # Assert
        assert 'nextCursor' in body
        assert body['nextCursor'] is not None
    
    @patch('src.functions.list_tickets.table')
    def test_customer_sees_only_own_tickets(self, mock_table):
        """
        GIVEN a customer user
        WHEN they list tickets
        THEN they should only see tickets they created
        """
        # Arrange
        customer_id = 'customer-123'
        mock_tickets = [
            {'ticketId': '1', 'createdBy': customer_id, 'status': 'OPEN'},
            {'ticketId': '2', 'createdBy': 'other-customer', 'status': 'OPEN'},
            {'ticketId': '3', 'createdBy': customer_id, 'status': 'CLOSED'}
        ]
        
        mock_table.scan.return_value = {'Items': mock_tickets}
        
        event = {
            'queryStringParameters': None,
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'sub': customer_id,
                        'custom:role': 'CUSTOMER'
                    }
                }
            }
        }
        
        # Act
        response = handler(event, {})
        body = json.loads(response['body'])
        
        # Assert
        assert response['statusCode'] == 200
        assert len(body['tickets']) == 2  # Only customer's tickets
        assert all(t['createdBy'] == customer_id for t in body['tickets'])
    
    @patch('src.functions.list_tickets.table')
    def test_agent_sees_all_tickets(self, mock_table):
        """
        GIVEN an agent user
        WHEN they list tickets
        THEN they should see all tickets
        """
        # Arrange
        mock_tickets = [
            {'ticketId': '1', 'createdBy': 'customer-1'},
            {'ticketId': '2', 'createdBy': 'customer-2'},
            {'ticketId': '3', 'createdBy': 'customer-3'}
        ]
        
        mock_table.scan.return_value = {'Items': mock_tickets}
        
        event = {
            'queryStringParameters': None,
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
        body = json.loads(response['body'])
        
        # Assert
        assert len(body['tickets']) == 3  # All tickets


class TestFilterTicketsByRole:
    """Test suite for role-based filtering logic"""
    
    def test_admin_sees_all_tickets(self):
        """Admins should see all tickets"""
        tickets = [
            {'createdBy': 'user-1'},
            {'createdBy': 'user-2'},
            {'createdBy': 'user-3'}
        ]
        
        filtered = filter_tickets_by_role(tickets, 'admin-123', 'ADMIN')
        
        assert len(filtered) == 3
    
    def test_agent_sees_all_tickets(self):
        """Agents should see all tickets"""
        tickets = [
            {'createdBy': 'user-1'},
            {'createdBy': 'user-2'}
        ]
        
        filtered = filter_tickets_by_role(tickets, 'agent-123', 'AGENT')
        
        assert len(filtered) == 2
    
    def test_customer_sees_only_own_tickets(self):
        """Customers should only see their own tickets"""
        customer_id = 'customer-123'
        tickets = [
            {'createdBy': customer_id, 'ticketId': '1'},
            {'createdBy': 'other-customer', 'ticketId': '2'},
            {'createdBy': customer_id, 'ticketId': '3'}
        ]
        
        filtered = filter_tickets_by_role(tickets, customer_id, 'CUSTOMER')
        
        assert len(filtered) == 2
        assert all(t['createdBy'] == customer_id for t in filtered)
    
    def test_unknown_role_sees_nothing(self):
        """Unknown roles should see no tickets"""
        tickets = [{'createdBy': 'user-1'}]
        
        filtered = filter_tickets_by_role(tickets, 'user-1', 'UNKNOWN_ROLE')
        
        assert len(filtered) == 0


class TestPaginationCursors:
    """Test suite for pagination cursor encoding/decoding"""
    
    def test_encode_decode_cursor_roundtrip(self):
        """Cursor should encode and decode correctly"""
        original_key = {
            'ticketId': 'test-123',
            'createdAt': '2026-01-19T10:00:00Z'
        }
        
        # Encode
        cursor = encode_cursor(original_key)
        assert isinstance(cursor, str)
        
        # Decode
        decoded_key = decode_cursor(cursor)
        assert decoded_key == original_key
    
    def test_cursor_is_base64_encoded(self):
        """Cursor should be valid base64"""
        import base64
        
        key = {'ticketId': 'test'}
        cursor = encode_cursor(key)
        
        # Should not raise exception
        base64.b64decode(cursor.encode())