"""
Lambda function handler for creating tickets.
This demonstrates TDD approach - tests written first!
"""
import json
import uuid
from datetime import datetime
from typing import Dict, Any


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for POST /tickets
    
    Args:
        event: API Gateway event with ticket data in body
        context: Lambda context (unused)
    
    Returns:
        API Gateway response with created ticket
    """
    # TODO: This is a minimal implementation
    # We'll expand it through TDD!
    
    try:
        # Parse request body
        body = json.loads(event.get('body', '{}'))
        
        # Extract required fields
        title = body.get('title')
        description = body.get('description')
        
        # Basic validation
        if not title:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Title is required'})
            }
        
        if not description:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Description is required'})
            }
        
        # Create ticket (simplified - no DB yet)
        ticket = {
            'ticketId': str(uuid.uuid4()),
            'title': title,
            'description': description,
            'status': 'OPEN',
            'priority': body.get('priority', 'MEDIUM'),
            'createdAt': datetime.utcnow().isoformat(),
            'createdBy': 'user123'  # TODO: Get from JWT token
        }
        
        # TODO: Save to DynamoDB
        
        return {
            'statusCode': 201,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps(ticket)
        }
        
    except json.JSONDecodeError:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'Invalid JSON'})
        }
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'Internal server error'})
        }