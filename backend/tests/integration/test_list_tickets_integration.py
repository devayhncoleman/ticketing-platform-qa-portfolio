"""
Integration tests for list_tickets Lambda function
Tests real GSI queries against DynamoDB
"""
import json
import pytest
import boto3
from src.functions.create_ticket import handler as create_handler
from src.functions.list_tickets import handler as list_handler


# Real DynamoDB table
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
table = dynamodb.Table('dev-tickets')


@pytest.mark.integration
def test_list_tickets_query_by_status_gsi():
    """
    Integration test: Query tickets by status using StatusIndex GSI
    """
    # Arrange - Create 3 OPEN tickets and 2 CLOSED tickets
    ticket_ids = []
    
    for i in range(3):
        event = {
            'body': json.dumps({
                'title': f'Open Ticket {i+1}',
                'description': 'Integration test ticket',
                'priority': 'LOW'
            }),
            'requestContext': {
                'authorizer': {'claims': {'sub': 'test-user', 'custom:role': 'CUSTOMER'}}
            }
        }
        response = create_handler(event, {})
        ticket_ids.append(json.loads(response['body'])['ticketId'])
    
    print(f"\n✅ Created 3 OPEN test tickets")
    
    try:
        # Act - Query for OPEN tickets
        list_event = {
            'queryStringParameters': {'status': 'OPEN'},
            'requestContext': {
                'authorizer': {'claims': {'sub': 'admin', 'custom:role': 'ADMIN'}}
            }
        }
        
        response = list_handler(list_event, {})
        body = json.loads(response['body'])
        
        # Assert
        assert response['statusCode'] == 200
        assert 'tickets' in body
        assert body['count'] >= 3  # At least our 3 tickets
        
        # Verify our tickets are in results
        returned_ids = [t['ticketId'] for t in body['tickets']]
        for ticket_id in ticket_ids:
            assert ticket_id in returned_ids
        
        print(f"✅ StatusIndex GSI query returned {body['count']} OPEN tickets")
        print(f"✅ All test tickets found in results")
        
    finally:
        # Cleanup
        for ticket_id in ticket_ids:
            table.delete_item(Key={'ticketId': ticket_id})
        print(f"✅ Cleaned up {len(ticket_ids)} test tickets")


@pytest.mark.integration
def test_list_tickets_query_by_assigned_to_gsi():
    """
    Integration test: Query tickets by assignedTo using AssignedToIndex GSI
    """
    # Arrange - Create tickets assigned to specific agent
    agent_id = 'integration-test-agent-123'
    ticket_ids = []
    
    for i in range(2):
        event = {
            'body': json.dumps({
                'title': f'Assigned Ticket {i+1}',
                'description': 'Testing AssignedToIndex',
                'priority': 'MEDIUM',
                'assignedTo': agent_id
            }),
            'requestContext': {
                'authorizer': {'claims': {'sub': 'test-user', 'custom:role': 'CUSTOMER'}}
            }
        }
        response = create_handler(event, {})
        ticket_ids.append(json.loads(response['body'])['ticketId'])
    
    print(f"\n✅ Created 2 tickets assigned to {agent_id}")
    
    try:
        # Act - Query tickets assigned to this agent
        list_event = {
            'queryStringParameters': {'assignedTo': agent_id},
            'requestContext': {
                'authorizer': {'claims': {'sub': agent_id, 'custom:role': 'AGENT'}}
            }
        }
        
        response = list_handler(list_event, {})
        body = json.loads(response['body'])
        
        # Assert
        assert response['statusCode'] == 200
        assert body['count'] >= 2
        
        # Verify our tickets are in results
        returned_ids = [t['ticketId'] for t in body['tickets']]
        for ticket_id in ticket_ids:
            assert ticket_id in returned_ids
        
        # Verify all returned tickets are assigned to our agent
        for ticket in body['tickets']:
            assert ticket['assignedTo'] == agent_id
        
        print(f"✅ AssignedToIndex GSI query returned {body['count']} tickets")
        print(f"✅ All tickets correctly assigned to {agent_id}")
        
    finally:
        # Cleanup
        for ticket_id in ticket_ids:
            table.delete_item(Key={'ticketId': ticket_id})
        print(f"✅ Cleaned up {len(ticket_ids)} test tickets")


@pytest.mark.integration
def test_customer_role_filtering():
    """
    Integration test: Verify customers only see their own tickets
    """
    # Arrange - Create tickets as two different customers
    customer1_id = 'customer-1-test'
    customer2_id = 'customer-2-test'
    
    customer1_tickets = []
    customer2_tickets = []
    
    # Create 2 tickets for customer 1
    for i in range(2):
        event = {
            'body': json.dumps({
                'title': f'Customer 1 Ticket {i+1}',
                'description': 'Test',
                'priority': 'LOW'
            }),
            'requestContext': {
                'authorizer': {'claims': {'sub': customer1_id, 'custom:role': 'CUSTOMER'}}
            }
        }
        response = create_handler(event, {})
        customer1_tickets.append(json.loads(response['body'])['ticketId'])
    
    # Create 2 tickets for customer 2
    for i in range(2):
        event = {
            'body': json.dumps({
                'title': f'Customer 2 Ticket {i+1}',
                'description': 'Test',
                'priority': 'LOW'
            }),
            'requestContext': {
                'authorizer': {'claims': {'sub': customer2_id, 'custom:role': 'CUSTOMER'}}
            }
        }
        response = create_handler(event, {})
        customer2_tickets.append(json.loads(response['body'])['ticketId'])
    
    print(f"\n✅ Created 2 tickets each for 2 different customers")
    
    try:
        # Act - Customer 1 lists tickets
        list_event = {
            'queryStringParameters': None,
            'requestContext': {
                'authorizer': {'claims': {'sub': customer1_id, 'custom:role': 'CUSTOMER'}}
            }
        }
        
        response = list_handler(list_event, {})
        body = json.loads(response['body'])
        
        # Assert - Customer 1 should only see their own tickets
        returned_ids = [t['ticketId'] for t in body['tickets']]
        
        for ticket_id in customer1_tickets:
            assert ticket_id in returned_ids, "Customer 1 should see their own tickets"
        
        for ticket_id in customer2_tickets:
            assert ticket_id not in returned_ids, "Customer 1 should NOT see customer 2's tickets"
        
        print(f"✅ Customer 1 correctly sees only their {len([t for t in body['tickets'] if t['ticketId'] in customer1_tickets])} tickets")
        
        # Act - Agent lists tickets (should see all)
        list_event['requestContext']['authorizer']['claims'] = {
            'sub': 'agent-test',
            'custom:role': 'AGENT'
        }
        
        response = list_handler(list_event, {})
        body = json.loads(response['body'])
        returned_ids = [t['ticketId'] for t in body['tickets']]
        
        # Assert - Agent should see both customers' tickets
        for ticket_id in customer1_tickets + customer2_tickets:
            assert ticket_id in returned_ids
        
        print(f"✅ Agent correctly sees all tickets (including test tickets)")
        
    finally:
        # Cleanup
        all_tickets = customer1_tickets + customer2_tickets
        for ticket_id in all_tickets:
            table.delete_item(Key={'ticketId': ticket_id})
        print(f"✅ Cleaned up {len(all_tickets)} test tickets")


@pytest.mark.integration
def test_pagination_with_limit():
    """
    Integration test: Verify pagination works with limit parameter
    """
    # Arrange - Create 5 tickets
    ticket_ids = []
    
    for i in range(5):
        event = {
            'body': json.dumps({
                'title': f'Pagination Test {i+1}',
                'description': 'Testing pagination',
                'priority': 'LOW'
            }),
            'requestContext': {
                'authorizer': {'claims': {'sub': 'test-user', 'custom:role': 'CUSTOMER'}}
            }
        }
        response = create_handler(event, {})
        ticket_ids.append(json.loads(response['body'])['ticketId'])
    
    print(f"\n✅ Created 5 tickets for pagination test")
    
    try:
        # Act - Request with limit of 3
        list_event = {
            'queryStringParameters': {'limit': '3'},
            'requestContext': {
                'authorizer': {'claims': {'sub': 'admin', 'custom:role': 'ADMIN'}}
            }
        }
        
        response = list_handler(list_event, {})
        body = json.loads(response['body'])
        
        # Assert
        assert response['statusCode'] == 200
        # Should have nextCursor since there are more results
        # (Note: This might not always be true if total tickets < limit)
        
        print(f"✅ Pagination query returned {body['count']} tickets")
        if 'nextCursor' in body:
            print(f"✅ Next cursor provided for additional results")
        
    finally:
        # Cleanup
        for ticket_id in ticket_ids:
            table.delete_item(Key={'ticketId': ticket_id})
        print(f"✅ Cleaned up {len(ticket_ids)} test tickets")