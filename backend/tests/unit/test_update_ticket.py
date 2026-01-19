"""
Unit tests for update_ticket Lambda function.
Tests validation, authorization, and optimistic locking.
"""
import json
import pytest
from unittest.mock import patch, MagicMock
from botocore.exceptions import ClientError
from src.functions.update_ticket import (
    handler,
    is_authorized_to_update,
    validate_update_fields,
    build_update_expression
)


class TestUpdateTicket:
    """Test suite for update ticket functionality"""
    
    @patch('src.functions.update_ticket.table')
    def test_update_ticket_status_returns_200(self, mock_table):
        """
        GIVEN valid ticket ID and status update
        WHEN update_ticket handler is called
        THEN it should update and return 200
        """
        # Arrange
        ticket_id = 'test-ticket-123'
        existing_ticket = {
            'ticketId': ticket_id,
            'status': 'OPEN',
            'createdBy': 'user-123'
        }
        
        updated_ticket = {**existing_ticket, 'status': 'IN_PROGRESS'}
        
        mock_table.get_item.return_value = {'Item': existing_ticket}
        mock_table.update_item.return_value = {'Attributes': updated_ticket}
        
        event = {
            'pathParameters': {'id': ticket_id},
            'body': json.dumps({'status': 'IN_PROGRESS'}),
            'requestContext': {
                'authorizer': {'claims': {'sub': 'agent-123', 'custom:role': 'AGENT'}}
            }
        }
        
        # Act
        response = handler(event, {})
        body = json.loads(response['body'])
        
        # Assert
        assert response['statusCode'] == 200
        assert body['status'] == 'IN_PROGRESS'
        mock_table.update_item.assert_called_once()
    
    @patch('src.functions.update_ticket.table')
    def test_update_ticket_priority_returns_200(self, mock_table):
        """Test updating ticket priority"""
        ticket_id = 'test-123'
        existing = {'ticketId': ticket_id, 'createdBy': 'user-1', 'priority': 'LOW'}
        updated = {**existing, 'priority': 'HIGH'}
        
        mock_table.get_item.return_value = {'Item': existing}
        mock_table.update_item.return_value = {'Attributes': updated}
        
        event = {
            'pathParameters': {'id': ticket_id},
            'body': json.dumps({'priority': 'HIGH'}),
            'requestContext': {
                'authorizer': {'claims': {'sub': 'user-1', 'custom:role': 'CUSTOMER'}}
            }
        }
        
        response = handler(event, {})
        assert response['statusCode'] == 200
    
    @patch('src.functions.update_ticket.table')
    def test_update_ticket_without_id_returns_400(self, mock_table):
        """Test missing ticket ID"""
        event = {
            'pathParameters': {},
            'body': json.dumps({'status': 'OPEN'}),
            'requestContext': {}
        }
        
        response = handler(event, {})
        body = json.loads(response['body'])
        
        assert response['statusCode'] == 400
        assert 'Ticket ID is required' in body['error']
    
    @patch('src.functions.update_ticket.table')
    def test_update_ticket_without_body_returns_400(self, mock_table):
        """Test missing request body"""
        event = {
            'pathParameters': {'id': 'test-123'},
            'body': json.dumps({}),
            'requestContext': {}
        }
        
        response = handler(event, {})
        body = json.loads(response['body'])
        
        assert response['statusCode'] == 400
        assert 'Update data is required' in body['error']
    
    @patch('src.functions.update_ticket.table')
    def test_update_nonexistent_ticket_returns_404(self, mock_table):
        """Test updating ticket that doesn't exist"""
        mock_table.get_item.return_value = {}  # No Item
        
        event = {
            'pathParameters': {'id': 'nonexistent'},
            'body': json.dumps({'status': 'OPEN'}),
            'requestContext': {
                'authorizer': {'claims': {'sub': 'user-1', 'custom:role': 'ADMIN'}}
            }
        }
        
        response = handler(event, {})
        assert response['statusCode'] == 404
    
    @patch('src.functions.update_ticket.table')
    def test_customer_cannot_update_others_ticket(self, mock_table):
        """Test customer authorization - cannot update other's tickets"""
        existing = {'ticketId': '123', 'createdBy': 'other-customer'}
        mock_table.get_item.return_value = {'Item': existing}
        
        event = {
            'pathParameters': {'id': '123'},
            'body': json.dumps({'status': 'CLOSED'}),
            'requestContext': {
                'authorizer': {'claims': {'sub': 'customer-1', 'custom:role': 'CUSTOMER'}}
            }
        }
        
        response = handler(event, {})
        body = json.loads(response['body'])
        
        assert response['statusCode'] == 403
        assert 'not authorized' in body['error'].lower()
    
    @patch('src.functions.update_ticket.table')
    def test_agent_can_update_any_ticket(self, mock_table):
        """Test agent can update any ticket"""
        existing = {'ticketId': '123', 'createdBy': 'customer-999'}
        updated = {**existing, 'status': 'IN_PROGRESS'}
        
        mock_table.get_item.return_value = {'Item': existing}
        mock_table.update_item.return_value = {'Attributes': updated}
        
        event = {
            'pathParameters': {'id': '123'},
            'body': json.dumps({'status': 'IN_PROGRESS'}),
            'requestContext': {
                'authorizer': {'claims': {'sub': 'agent-1', 'custom:role': 'AGENT'}}
            }
        }
        
        response = handler(event, {})
        assert response['statusCode'] == 200
    
    @patch('src.functions.update_ticket.table')
    def test_update_invalid_field_returns_400(self, mock_table):
        """Test updating invalid/immutable field"""
        existing = {'ticketId': '123', 'createdBy': 'user-1'}
        mock_table.get_item.return_value = {'Item': existing}
        
        event = {
            'pathParameters': {'id': '123'},
            'body': json.dumps({'ticketId': 'new-id'}),  # Immutable!
            'requestContext': {
                'authorizer': {'claims': {'sub': 'user-1', 'custom:role': 'ADMIN'}}
            }
        }
        
        response = handler(event, {})
        body = json.loads(response['body'])
        
        assert response['statusCode'] == 400
        assert 'Invalid fields' in body['error']
    
    @patch('src.functions.update_ticket.table')
    def test_update_invalid_status_returns_400(self, mock_table):
        """Test invalid status value"""
        existing = {'ticketId': '123', 'createdBy': 'user-1'}
        mock_table.get_item.return_value = {'Item': existing}
        
        event = {
            'pathParameters': {'id': '123'},
            'body': json.dumps({'status': 'INVALID_STATUS'}),
            'requestContext': {
                'authorizer': {'claims': {'sub': 'user-1', 'custom:role': 'ADMIN'}}
            }
        }
        
        response = handler(event, {})
        body = json.loads(response['body'])
        
        assert response['statusCode'] == 400
        assert 'Invalid status' in body['error']
    
    @patch('src.functions.update_ticket.table')
    def test_resolve_without_resolution_returns_400(self, mock_table):
        """Test setting status to RESOLVED without resolution"""
        existing = {'ticketId': '123', 'createdBy': 'user-1'}
        mock_table.get_item.return_value = {'Item': existing}
        
        event = {
            'pathParameters': {'id': '123'},
            'body': json.dumps({'status': 'RESOLVED'}),  # Missing resolution!
            'requestContext': {
                'authorizer': {'claims': {'sub': 'user-1', 'custom:role': 'AGENT'}}
            }
        }
        
        response = handler(event, {})
        body = json.loads(response['body'])
        
        assert response['statusCode'] == 400
        assert 'Resolution is required' in body['error']
    
    @patch('src.functions.update_ticket.table')
    def test_optimistic_locking_conflict_returns_409(self, mock_table):
        """Test concurrent modification conflict"""
        existing = {'ticketId': '123', 'createdBy': 'user-1'}
        mock_table.get_item.return_value = {'Item': existing}
        
        # Simulate concurrent modification
        error = ClientError(
            {'Error': {'Code': 'ConditionalCheckFailedException'}},
            'UpdateItem'
        )
        mock_table.update_item.side_effect = error
        
        event = {
            'pathParameters': {'id': '123'},
            'body': json.dumps({'status': 'IN_PROGRESS'}),
            'requestContext': {
                'authorizer': {'claims': {'sub': 'user-1', 'custom:role': 'AGENT'}}
            }
        }
        
        response = handler(event, {})
        body = json.loads(response['body'])
        
        assert response['statusCode'] == 409
        assert 'modified by another process' in body['error'].lower()


class TestValidateUpdateFields:
    """Test validation logic"""
    
    def test_valid_status_update(self):
        """Valid status should pass"""
        updates = {'status': 'IN_PROGRESS'}
        existing = {'status': 'OPEN'}
        
        error = validate_update_fields(updates, existing)
        assert error is None
    
    def test_invalid_field_rejected(self):
        """Invalid field should be rejected"""
        updates = {'createdBy': 'hacker'}  # Immutable!
        existing = {}
        
        error = validate_update_fields(updates, existing)
        assert error is not None
        assert 'Invalid fields' in error
    
    def test_resolved_requires_resolution(self):
        """RESOLVED status requires resolution"""
        updates = {'status': 'RESOLVED'}
        existing = {}
        
        error = validate_update_fields(updates, existing)
        assert error is not None
        assert 'Resolution is required' in error


class TestBuildUpdateExpression:
    """Test update expression building"""
    
    def test_builds_correct_expression(self):
        """Should build valid DynamoDB update expression"""
        updates = {'status': 'IN_PROGRESS', 'priority': 'HIGH'}
        user_id = 'user-123'
        
        expr, names, values = build_update_expression(updates, user_id)
        
        assert 'SET' in expr
        assert '#updatedAt' in names
        assert '#updatedBy' in names
        assert ':updatedAt' in values
        assert ':updatedBy' in values
        assert values[':updatedBy'] == user_id
    
    def test_sets_resolved_at_when_resolved(self):
        """Should set resolvedAt when status=RESOLVED"""
        updates = {'status': 'RESOLVED', 'resolution': 'Fixed'}
        user_id = 'user-123'
        
        expr, names, values = build_update_expression(updates, user_id)
        
        assert '#resolvedAt' in names
        assert ':resolvedAt' in values