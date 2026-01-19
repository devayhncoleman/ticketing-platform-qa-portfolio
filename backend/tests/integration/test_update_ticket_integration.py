"""
Integration tests for update_ticket Lambda function
Tests real DynamoDB updates with authorization
"""
import json
import pytest
import boto3
from src.functions.create_ticket import handler as create_handler
from src.functions.update_ticket import handler as update_handler
from src.functions.get_ticket import handler as get_handler


# Real DynamoDB table
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
table = dynamodb.Table('dev-tickets')


@pytest.mark.integration
def test_update_ticket_status_in_dynamodb():
    """
    Integration test: Update ticket status and verify in DynamoDB
    """
    # Arrange - Create a ticket
    create_event = {
        'body': json.dumps({
            'title': 'Update Test Ticket',
            'description': 'Testing update functionality',
            'priority': 'LOW'
        }),
        'requestContext': {
            'authorizer': {'claims': {'sub': 'test-agent', 'custom:role': 'AGENT'}}
        }
    }
    
    create_response = create_handler(create_event, {})
    ticket = json.loads(create_response['body'])
    ticket_id = ticket['ticketId']
    
    print(f"\n✅ Created ticket: {ticket_id} with status: {ticket['status']}")
    
    try:
        # Act - Update the status
        update_event = {
            'pathParameters': {'id': ticket_id},
            'body': json.dumps({'status': 'IN_PROGRESS'}),
            'requestContext': {
                'authorizer': {'claims': {'sub': 'test-agent', 'custom:role': 'AGENT'}}
            }
        }
        
        update_response = update_handler(update_event, {})
        updated_ticket = json.loads(update_response['body'])
        
        # Assert - Response
        assert update_response['statusCode'] == 200
        assert updated_ticket['status'] == 'IN_PROGRESS'
        assert updated_ticket['ticketId'] == ticket_id
        
        # Verify in DynamoDB
        db_response = table.get_item(Key={'ticketId': ticket_id})
        db_ticket = db_response['Item']
        
        assert db_ticket['status'] == 'IN_PROGRESS'
        assert 'updatedAt' in db_ticket
        assert 'updatedBy' in db_ticket
        
        print(f"✅ Status updated to IN_PROGRESS in DynamoDB")
        print(f"✅ UpdatedAt: {db_ticket['updatedAt']}")
        print(f"✅ UpdatedBy: {db_ticket['updatedBy']}")
        
    finally:
        # Cleanup
        table.delete_item(Key={'ticketId': ticket_id})
        print(f"✅ Cleaned up test ticket")


@pytest.mark.integration
def test_resolve_ticket_with_resolution():
    """
    Integration test: Resolve ticket with resolution text
    """
    # Arrange - Create ticket
    create_event = {
        'body': json.dumps({
            'title': 'Bug Report',
            'description': 'App crashes on login',
            'priority': 'HIGH'
        }),
        'requestContext': {
            'authorizer': {'claims': {'sub': 'customer-1', 'custom:role': 'CUSTOMER'}}
        }
    }
    
    create_response = create_handler(create_event, {})
    ticket_id = json.loads(create_response['body'])['ticketId']
    
    print(f"\n✅ Created bug ticket: {ticket_id}")
    
    try:
        # Act - Resolve with resolution
        update_event = {
            'pathParameters': {'id': ticket_id},
            'body': json.dumps({
                'status': 'RESOLVED',
                'resolution': 'Updated authentication library to v2.0'
            }),
            'requestContext': {
                'authorizer': {'claims': {'sub': 'agent-1', 'custom:role': 'AGENT'}}
            }
        }
        
        update_response = update_handler(update_event, {})
        updated_ticket = json.loads(update_response['body'])
        
        # Assert
        assert update_response['statusCode'] == 200
        assert updated_ticket['status'] == 'RESOLVED'
        assert updated_ticket['resolution'] == 'Updated authentication library to v2.0'
        assert 'resolvedAt' in updated_ticket
        
        # Verify in DynamoDB
        db_response = table.get_item(Key={'ticketId': ticket_id})
        db_ticket = db_response['Item']
        
        assert db_ticket['status'] == 'RESOLVED'
        assert db_ticket['resolvedAt'] is not None
        
        print(f"✅ Ticket resolved successfully")
        print(f"✅ Resolution: {db_ticket['resolution']}")
        print(f"✅ Resolved at: {db_ticket['resolvedAt']}")
        
    finally:
        table.delete_item(Key={'ticketId': ticket_id})
        print(f"✅ Cleaned up test ticket")


@pytest.mark.integration
def test_customer_cannot_update_others_ticket():
    """
    Integration test: Verify customer authorization rules
    """
    # Arrange - Customer 1 creates ticket
    create_event = {
        'body': json.dumps({
            'title': 'Customer 1 Ticket',
            'description': 'Testing authorization',
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
        # Act - Customer 2 tries to update
        update_event = {
            'pathParameters': {'id': ticket_id},
            'body': json.dumps({'priority': 'CRITICAL'}),
            'requestContext': {
                'authorizer': {'claims': {'sub': 'customer-2', 'custom:role': 'CUSTOMER'}}
            }
        }
        
        update_response = update_handler(update_event, {})
        
        # Assert - Should be forbidden
        assert update_response['statusCode'] == 403
        print(f"✅ Customer 2 correctly denied access (403)")
        
        # Verify ticket unchanged in DynamoDB
        db_response = table.get_item(Key={'ticketId': ticket_id})
        db_ticket = db_response['Item']
        assert db_ticket['priority'] != 'CRITICAL'
        
        print(f"✅ Ticket remains unchanged (priority still: {db_ticket['priority']})")
        
    finally:
        table.delete_item(Key={'ticketId': ticket_id})
        print(f"✅ Cleaned up test ticket")


@pytest.mark.integration
def test_update_multiple_fields_simultaneously():
    """
    Integration test: Update multiple fields in one request
    """
    # Arrange
    create_event = {
        'body': json.dumps({
            'title': 'Multi-field Update Test',
            'description': 'Testing multiple updates',
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
        # Act - Update multiple fields
        update_event = {
            'pathParameters': {'id': ticket_id},
            'body': json.dumps({
                'status': 'IN_PROGRESS',
                'priority': 'HIGH',
                'assignedTo': 'agent-1',
                'tags': ['bug', 'urgent']
            }),
            'requestContext': {
                'authorizer': {'claims': {'sub': 'agent-1', 'custom:role': 'AGENT'}}
            }
        }
        
        update_response = update_handler(update_event, {})
        updated_ticket = json.loads(update_response['body'])
        
        # Assert
        assert update_response['statusCode'] == 200
        assert updated_ticket['status'] == 'IN_PROGRESS'
        assert updated_ticket['priority'] == 'HIGH'
        assert updated_ticket['assignedTo'] == 'agent-1'
        assert updated_ticket['tags'] == ['bug', 'urgent']
        
        print(f"✅ Multiple fields updated successfully:")
        print(f"   - Status: {updated_ticket['status']}")
        print(f"   - Priority: {updated_ticket['priority']}")
        print(f"   - Assigned to: {updated_ticket['assignedTo']}")
        print(f"   - Tags: {updated_ticket['tags']}")
        
    finally:
        table.delete_item(Key={'ticketId': ticket_id})
        print(f"✅ Cleaned up test ticket")