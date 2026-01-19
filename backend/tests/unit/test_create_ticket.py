"""
Unit tests for create_ticket Lambda function.
Demonstrates Test-Driven Development (TDD) approach.
"""
import json
import pytest
from src.functions.create_ticket import handler


class TestCreateTicket:
    """Test suite for create ticket functionality"""
    
    def test_create_ticket_with_valid_data_returns_201(self):
        """
        GIVEN valid ticket data in request body
        WHEN create_ticket handler is called
        THEN it should return 201 status code with ticket details
        """
        # Arrange
        event = {
            'body': json.dumps({
                'title': 'Login Issue',
                'description': 'Cannot access my account',
                'priority': 'HIGH'
            }),
            'requestContext': {}
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
        assert body['assignedTo'] == 'UNASSIGNED'
        assert 'createdAt' in body
    
    def test_create_ticket_without_title_returns_400(self):
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
            'requestContext': {}
        }
        
        # Act
        response = handler(event, {})
        body = json.loads(response['body'])
        
        # Assert
        assert response['statusCode'] == 400
        assert 'error' in body
        assert 'Title is required' in body['error']
    
    def test_create_ticket_without_description_returns_400(self):
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
            'requestContext': {}
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
            'requestContext': {}
        }
        
        # Act
        response = handler(event, {})
        body = json.loads(response['body'])
        
        # Assert
        assert response['statusCode'] == 400
        assert 'error' in body
    
    def test_create_ticket_assigns_defaults(self):
        """
        GIVEN request without priority or assignedTo
        WHEN create_ticket handler is called
        THEN it should assign default values
        """
        # Arrange
        event = {
            'body': json.dumps({
                'title': 'Test Ticket',
                'description': 'Test Description'
            }),
            'requestContext': {}
        }
        
        # Act
        response = handler(event, {})
        body = json.loads(response['body'])
        
        # Assert
        assert response['statusCode'] == 201
        assert body['priority'] == 'MEDIUM'
        assert body['assignedTo'] == 'UNASSIGNED'
    
    def test_create_ticket_generates_unique_ticket_id(self):
        """
        GIVEN multiple ticket creation requests
        WHEN tickets are created
        THEN each should have a unique ticket ID
        """
        # Arrange
        event = {
            'body': json.dumps({
                'title': 'Test Ticket',
                'description': 'Test Description'
            }),
            'requestContext': {}
        }
        
        # Act
        response1 = handler(event, {})
        response2 = handler(event, {})
        
        ticket1 = json.loads(response1['body'])
        ticket2 = json.loads(response2['body'])
        
        # Assert
        assert ticket1['ticketId'] != ticket2['ticketId']
    
    def test_create_ticket_with_invalid_priority_returns_400(self):
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
            'requestContext': {}
        }
        
        # Act
        response = handler(event, {})
        body = json.loads(response['body'])
        
        # Assert
        assert response['statusCode'] == 400
        assert 'error' in body
        assert 'Invalid priority' in body['error']