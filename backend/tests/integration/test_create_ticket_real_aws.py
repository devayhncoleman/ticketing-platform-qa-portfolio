"""
Integration test - hits REAL DynamoDB!
"""
import json
import pytest
import boto3
from src.functions.create_ticket import handler


# Real DynamoDB table
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
table = dynamodb.Table('dev-tickets')


@pytest.mark.integration
def test_create_ticket_saves_to_real_dynamodb():
    """
    🚀 INTEGRATION TEST - This hits REAL AWS!
    """
    # Arrange
    event = {
        'body': json.dumps({
            'title': '🎉 My First Real AWS Ticket!',
            'description': 'This is actually being saved to DynamoDB in AWS!',
            'priority': 'HIGH'
        }),
        'requestContext': {}
    }
    
    # Act - Call the Lambda handler
    response = handler(event, {})
    body = json.loads(response['body'])
    ticket_id = body['ticketId']
    
    print(f"\n✅ Created ticket: {ticket_id}")
    
    # Assert - Check response
    assert response['statusCode'] == 201
    assert body['title'] == '🎉 My First Real AWS Ticket!'
    assert body['status'] == 'OPEN'
    assert body['assignedTo'] == 'UNASSIGNED'  # ✅ Check default
    
    # 🎯 THE BIG MOMENT - Check if it's ACTUALLY in DynamoDB!
    db_response = table.get_item(Key={'ticketId': ticket_id})
    assert 'Item' in db_response
    
    db_ticket = db_response['Item']
    assert db_ticket['title'] == '🎉 My First Real AWS Ticket!'
    assert db_ticket['priority'] == 'HIGH'
    assert db_ticket['assignedTo'] == 'UNASSIGNED'
    
    print(f"✅ Verified ticket exists in DynamoDB!")
    print(f"✅ Ticket data: {json.dumps(db_ticket, indent=2, default=str)}")
    
    # Cleanup
    table.delete_item(Key={'ticketId': ticket_id})
    print(f"✅ Cleaned up test ticket")


@pytest.mark.integration
def test_query_unassigned_tickets_using_gsi():
    """
    Integration test: Verify AssignedToIndex GSI works
    """
    # Create 2 unassigned tickets
    ticket_ids = []
    for i in range(2):
        event = {
            'body': json.dumps({
                'title': f'Unassigned Ticket {i+1}',
                'description': 'Test GSI query',
                'priority': 'LOW'
            }),
            'requestContext': {}
        }
        
        response = handler(event, {})
        body = json.loads(response['body'])
        ticket_ids.append(body['ticketId'])
    
    # Query using AssignedToIndex GSI
    query_response = table.query(
        IndexName='AssignedToIndex',
        KeyConditionExpression='assignedTo = :assignedTo',
        ExpressionAttributeValues={':assignedTo': 'UNASSIGNED'}
    )
    
    # Assert: Our tickets should be in results
    tickets = query_response['Items']
    found_ticket_ids = [t['ticketId'] for t in tickets]
    
    for ticket_id in ticket_ids:
        assert ticket_id in found_ticket_ids
    
    print(f"✅ GSI query returned {len(tickets)} UNASSIGNED tickets")
    
    # Cleanup
    for ticket_id in ticket_ids:
        table.delete_item(Key={'ticketId': ticket_id})
    print(f"✅ Cleaned up test tickets")