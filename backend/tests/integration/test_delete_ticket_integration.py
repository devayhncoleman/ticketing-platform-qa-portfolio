"""
Integration tests for delete_ticket Lambda function
Tests soft and hard delete with real DynamoDB
"""
import json
import pytest
import boto3
from src.functions.create_ticket import handler as create_handler
from src.functions.delete_ticket import handler as delete_handler
from src.functions.get_ticket import handler as get_handler


# Real DynamoDB table
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
table = dynamodb.Table('dev-tickets')


@pytest.mark.integration
def test_soft_delete_sets_status_to_closed():
    """
    Integration test: Soft delete sets status to CLOSED in DynamoDB
    """
    # Arrange - Create a ticket
    create_event = {
        'body': json.dumps({
            'title': 'Soft Delete Test',
            'description': 'Testing soft delete',
            'priority': 'LOW'
        }),
        'requestContext': {
            'authorizer': {'claims': {'sub': 'agent-1', 'custom:role': 'AGENT'}}
        }
    }
    
    create_response = create_handler(create_event, {})
    ticket_id = json.loads(create_response['body'])['ticketId']
    
    print(f"\n✅ Created ticket: {ticket_id}")
    
    try:
        # Act - Soft delete (default)
        delete_event = {
            'pathParameters': {'id': ticket_id},
            'queryStringParameters': None,
            'requestContext': {
                'authorizer': {'claims': {'sub': 'agent-1', 'custom:role': 'AGENT'}}
            }
        }
        
        delete_response = delete_handler(delete_event, {})
        
        # Assert
        assert delete_response['statusCode'] == 204
        
        # Verify ticket still exists but is CLOSED
        db_response = table.get_item(Key={'ticketId': ticket_id})
        assert 'Item' in db_response
        assert db_response['Item']['status'] == 'CLOSED'
        
        print(f"✅ Ticket soft deleted (status = CLOSED)")
        print(f"✅ Ticket still exists in database")
        
    finally:
        # Cleanup - hard delete
        table.delete_item(Key={'ticketId': ticket_id})
        print(f"✅ Cleaned up test ticket")


@pytest.mark.integration
def test_hard_delete_removes_from_dynamodb():
    """
    Integration test: Hard delete permanently removes ticket
    """
    # Arrange - Create a ticket
    create_event = {
        'body': json.dumps({
            'title': 'Hard Delete Test',
            'description': 'Testing hard delete',
            'priority': 'LOW'
        }),
        'requestContext': {
            'authorizer': {'claims': {'sub': 'admin-1', 'custom:role': 'ADMIN'}}
        }
    }
    
    create_response = create_handler(create_event, {})
    ticket_id = json.loads(create_response['body'])['ticketId']
    
    print(f"\n✅ Created ticket: {ticket_id}")
    
    # Act - Hard delete
    delete_event = {
        'pathParameters': {'id': ticket_id},
        'queryStringParameters': {'hard': 'true'},
        'requestContext': {
            'authorizer': {'claims': {'sub': 'admin-1', 'custom:role': 'ADMIN'}}
        }
    }
    
    delete_response = delete_handler(delete_event, {})
    
    # Assert
    assert delete_response['statusCode'] == 204
    
    # Verify ticket is GONE from DynamoDB
    db_response = table.get_item(Key={'ticketId': ticket_id})
    assert 'Item' not in db_response
    
    print(f"✅ Ticket permanently deleted from DynamoDB")
    print(f"✅ Verified ticket does not exist")


@pytest.mark.integration
def test_customer_authorization_for_delete():
    """
    Integration test: Verify customer can only delete own tickets
    """
    # Arrange - Customer 1 creates ticket
    create_event = {
        'body': json.dumps({
            'title': 'Customer Delete Test',
            'description': 'Testing delete authorization',
            'priority': 'LOW'
        }),
        'requestContext': {
            'authorizer': {'claims': {'sub': 'customer-1', 'custom:role': 'CUSTOMER'}}
        }
    }
    
    create_response = create_handler(create_event, {})
    ticket_id = json.loads(create_response['body'])['ticketId']
    
    print(f"\n✅ Customer 1 created ticket: {ticket_id}")
    
    try:
        # Act - Customer 2 tries to delete
        delete_event = {
            'pathParameters': {'id': ticket_id},
            'queryStringParameters': None,
            'requestContext': {
                'authorizer': {'claims': {'sub': 'customer-2', 'custom:role': 'CUSTOMER'}}
            }
        }
        
        delete_response = delete_handler(delete_event, {})
        
        # Assert - Should be forbidden
        assert delete_response['statusCode'] == 403
        print(f"✅ Customer 2 correctly denied (403)")
        
        # Verify ticket still exists and unchanged
        db_response = table.get_item(Key={'ticketId': ticket_id})
        assert 'Item' in db_response
        assert db_response['Item']['status'] == 'OPEN'
        
        print(f"✅ Ticket remains unchanged (still OPEN)")
        
        # Now customer 1 deletes their own ticket - should succeed
        delete_event['requestContext']['authorizer']['claims']['sub'] = 'customer-1'
        delete_response = delete_handler(delete_event, {})
        
        assert delete_response['statusCode'] == 204
        print(f"✅ Customer 1 successfully deleted their own ticket")
        
        # Verify it's now CLOSED
        db_response = table.get_item(Key={'ticketId': ticket_id})
        assert db_response['Item']['status'] == 'CLOSED'
        
    finally:
        # Cleanup
        table.delete_item(Key={'ticketId': ticket_id})
        print(f"✅ Cleaned up test ticket")


@pytest.mark.integration
def test_agent_cannot_hard_delete():
    """
    Integration test: Verify only admins can hard delete
    """
    # Arrange - Create ticket
    create_event = {
        'body': json.dumps({
            'title': 'Agent Hard Delete Test',
            'description': 'Testing agent cannot hard delete',
            'priority': 'LOW'
        }),
        'requestContext': {
            'authorizer': {'claims': {'sub': 'agent-1', 'custom:role': 'AGENT'}}
        }
    }
    
    create_response = create_handler(create_event, {})
    ticket_id = json.loads(create_response['body'])['ticketId']
    
    print(f"\n✅ Created ticket: {ticket_id}")
    
    try:
        # Act - Agent tries to hard delete
        delete_event = {
            'pathParameters': {'id': ticket_id},
            'queryStringParameters': {'hard': 'true'},
            'requestContext': {
                'authorizer': {'claims': {'sub': 'agent-1', 'custom:role': 'AGENT'}}
            }
        }
        
        delete_response = delete_handler(delete_event, {})
        
        # Assert - Should be forbidden
        assert delete_response['statusCode'] == 403
        print(f"✅ Agent correctly denied hard delete (403)")
        
        # Verify ticket still exists
        db_response = table.get_item(Key={'ticketId': ticket_id})
        assert 'Item' in db_response
        
        print(f"✅ Ticket still exists in database")
        
    finally:
        # Cleanup
        table.delete_item(Key={'ticketId': ticket_id})
        print(f"✅ Cleaned up test ticket")