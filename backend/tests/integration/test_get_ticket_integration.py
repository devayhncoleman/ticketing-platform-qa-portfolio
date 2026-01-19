"""
Integration test for get_ticket Lambda function
Tests against real DynamoDB table
"""
import json
import pytest
import boto3
from src.functions.create_ticket import handler as create_handler
from src.functions.get_ticket import handler as get_handler


# Real DynamoDB table
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
table = dynamodb.Table('dev-tickets')


@pytest.mark.integration
def test_get_ticket_retrieves_from_real_dynamodb():
    """
    Integration test: Create a ticket, then retrieve it
    Verifies full round-trip with real DynamoDB
    """
    # Arrange - Create a ticket first
    create_event = {
        'body': json.dumps({
            'title': 'Integration Test - GET Ticket',
            'description': 'Testing ticket retrieval',
            'priority': 'MEDIUM'
        }),
        'requestContext': {
            'authorizer': {
                'claims': {
                    'sub': 'test-user-123',
                    'custom:role': 'CUSTOMER'
                }
            }
        }
    }
    
    create_response = create_handler(create_event, {})
    created_ticket = json.loads(create_response['body'])
    ticket_id = created_ticket['ticketId']
    
    print(f"\n✅ Created ticket for test: {ticket_id}")
    
    try:
        # Act - Retrieve the ticket
        get_event = {
            'pathParameters': {'id': ticket_id},
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'sub': 'test-user-123',
                        'custom:role': 'CUSTOMER'
                    }
                }
            }
        }
        
        get_response = get_handler(get_event, {})
        retrieved_ticket = json.loads(get_response['body'])
        
        # Assert
        assert get_response['statusCode'] == 200
        assert retrieved_ticket['ticketId'] == ticket_id
        assert retrieved_ticket['title'] == 'Integration Test - GET Ticket'
        assert retrieved_ticket['status'] == 'OPEN'
        assert retrieved_ticket['priority'] == 'MEDIUM'
        
        print(f"✅ Successfully retrieved ticket from DynamoDB")
        print(f"✅ Ticket data: {json.dumps(retrieved_ticket, indent=2, default=str)}")
        
    finally:
        # Cleanup
        table.delete_item(Key={'ticketId': ticket_id})
        print(f"✅ Cleaned up test ticket: {ticket_id}")


@pytest.mark.integration
def test_get_nonexistent_ticket_returns_404():
    """
    Integration test: Verify 404 for nonexistent ticket
    """
    # Arrange
    fake_ticket_id = 'nonexistent-ticket-12345'
    
    get_event = {
        'pathParameters': {'id': fake_ticket_id},
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
    response = get_handler(get_event, {})
    body = json.loads(response['body'])
    
    # Assert
    assert response['statusCode'] == 404
    assert 'error' in body
    assert 'not found' in body['error'].lower()
    
    print(f"✅ Correctly returned 404 for nonexistent ticket")


@pytest.mark.integration  
def test_customer_authorization_on_real_tickets():
    """
    Integration test: Verify customer can't access other customers' tickets
    """
    # Arrange - Create ticket as customer-1
    create_event = {
        'body': json.dumps({
            'title': 'Customer 1 Ticket',
            'description': 'Testing authorization',
            'priority': 'LOW'
        }),
        'requestContext': {
            'authorizer': {
                'claims': {
                    'sub': 'customer-1',
                    'custom:role': 'CUSTOMER'
                }
            }
        }
    }
    
    create_response = create_handler(create_event, {})
    created_ticket = json.loads(create_response['body'])
    ticket_id = created_ticket['ticketId']
    
    print(f"\n✅ Created ticket as customer-1: {ticket_id}")
    
    try:
        # Act - Try to retrieve as customer-2
        get_event = {
            'pathParameters': {'id': ticket_id},
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'sub': 'customer-2',  # Different customer!
                        'custom:role': 'CUSTOMER'
                    }
                }
            }
        }
        
        response = get_handler(get_event, {})
        body = json.loads(response['body'])
        
        # Assert - Should be forbidden
        assert response['statusCode'] == 403
        assert 'error' in body
        assert 'not authorized' in body['error'].lower()
        
        print(f"✅ Correctly denied access to customer-2")
        
        # Now try as AGENT - should succeed
        get_event['requestContext']['authorizer']['claims']['custom:role'] = 'AGENT'
        response = get_handler(get_event, {})
        
        assert response['statusCode'] == 200
        print(f"✅ Agent successfully accessed the ticket")
        
    finally:
        # Cleanup
        table.delete_item(Key={'ticketId': ticket_id})
        print(f"✅ Cleaned up test ticket: {ticket_id}")