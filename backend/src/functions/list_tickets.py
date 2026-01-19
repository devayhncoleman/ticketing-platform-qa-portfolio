"""
Lambda function handler for listing tickets with filtering.
GET /tickets?status=OPEN&assignedTo=agent-123&limit=20
"""
import json
import os
from typing import Dict, Any, Optional
import boto3
from botocore.exceptions import ClientError


# Initialize DynamoDB
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
table_name = os.environ.get('TICKETS_TABLE_NAME', 'dev-tickets')
table = dynamodb.Table(table_name)


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for GET /tickets
    Lists tickets with optional filtering by status or assignedTo
    
    Query parameters:
    - status: Filter by ticket status (uses StatusIndex GSI)
    - assignedTo: Filter by assigned agent (uses AssignedToIndex GSI)
    - limit: Maximum number of results (default: 50, max: 100)
    - cursor: Pagination token for next page
    
    Args:
        event: API Gateway event with query parameters
        context: Lambda context
    
    Returns:
        API Gateway response with list of tickets
    """
    try:
        # Extract query parameters
        query_params = event.get('queryStringParameters') or {}
        status_filter = query_params.get('status')
        assigned_to_filter = query_params.get('assignedTo')
        limit = int(query_params.get('limit', '50'))
        cursor = query_params.get('cursor')
        
        # Validate limit
        if limit > 100:
            return create_response(400, {
                'error': 'Limit cannot exceed 100'
            })
        
        # Get user info
        user_id = extract_user_id(event)
        user_role = extract_user_role(event)
        
        # Execute appropriate query based on filters
        if status_filter:
            result = query_by_status(status_filter, limit, cursor)
        elif assigned_to_filter:
            result = query_by_assigned_to(assigned_to_filter, limit, cursor)
        else:
            # No filters - scan table (less efficient, but necessary)
            result = scan_all_tickets(limit, cursor)
        
        tickets = result.get('Items', [])
        
        # Apply role-based filtering
        filtered_tickets = filter_tickets_by_role(tickets, user_id, user_role)
        
        # Prepare response with pagination
        response_body = {
            'tickets': filtered_tickets,
            'count': len(filtered_tickets)
        }
        
        # Add pagination cursor if more results available
        if 'LastEvaluatedKey' in result:
            response_body['nextCursor'] = encode_cursor(result['LastEvaluatedKey'])
        
        print(f"✅ Listed {len(filtered_tickets)} tickets for user: {user_id} (role: {user_role})")
        
        return create_response(200, response_body)
        
    except ValueError as e:
        return create_response(400, {'error': f'Invalid parameter: {str(e)}'})
    
    except ClientError as e:
        error_code = e.response['Error']['Code']
        print(f"DynamoDB error: {error_code} - {e}")
        return create_response(500, {'error': 'Failed to retrieve tickets'})
    
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")
        return create_response(500, {'error': 'Internal server error'})


def query_by_status(status: str, limit: int, cursor: Optional[str]) -> Dict[str, Any]:
    """
    Query tickets by status using StatusIndex GSI
    Returns tickets sorted by createdAt (newest first)
    """
    query_params = {
        'IndexName': 'StatusIndex',
        'KeyConditionExpression': '#status = :status',
        'ExpressionAttributeNames': {'#status': 'status'},
        'ExpressionAttributeValues': {':status': status.upper()},
        'Limit': limit,
        'ScanIndexForward': False  # Descending order (newest first)
    }
    
    if cursor:
        query_params['ExclusiveStartKey'] = decode_cursor(cursor)
    
    return table.query(**query_params)


def query_by_assigned_to(assigned_to: str, limit: int, cursor: Optional[str]) -> Dict[str, Any]:
    """
    Query tickets by assignedTo using AssignedToIndex GSI
    Returns tickets sorted by createdAt (newest first)
    """
    query_params = {
        'IndexName': 'AssignedToIndex',
        'KeyConditionExpression': 'assignedTo = :assignedTo',
        'ExpressionAttributeValues': {':assignedTo': assigned_to},
        'Limit': limit,
        'ScanIndexForward': False
    }
    
    if cursor:
        query_params['ExclusiveStartKey'] = decode_cursor(cursor)
    
    return table.query(**query_params)


def scan_all_tickets(limit: int, cursor: Optional[str]) -> Dict[str, Any]:
    """
    Scan all tickets (no filter)
    Note: This is less efficient than queries, but necessary when no filter provided
    In production, consider requiring at least one filter parameter
    """
    scan_params = {
        'Limit': limit
    }
    
    if cursor:
        scan_params['ExclusiveStartKey'] = decode_cursor(cursor)
    
    return table.scan(**scan_params)


def filter_tickets_by_role(tickets: list, user_id: str, user_role: str) -> list:
    """
    Filter tickets based on user role
    
    Rules:
    - ADMIN: See all tickets
    - AGENT: See all tickets
    - CUSTOMER: See only tickets they created
    """
    if user_role in ['ADMIN', 'AGENT']:
        return tickets
    
    if user_role == 'CUSTOMER':
        return [t for t in tickets if t.get('createdBy') == user_id]
    
    # Unknown role - return empty list
    return []


def encode_cursor(last_key: Dict[str, Any]) -> str:
    """
    Encode LastEvaluatedKey as base64 cursor for pagination
    """
    import base64
    cursor_json = json.dumps(last_key, default=str)
    return base64.b64encode(cursor_json.encode()).decode()


def decode_cursor(cursor: str) -> Dict[str, Any]:
    """
    Decode base64 cursor back to DynamoDB key
    """
    import base64
    cursor_json = base64.b64decode(cursor.encode()).decode()
    return json.loads(cursor_json)


def extract_user_id(event: Dict[str, Any]) -> str:
    """Extract user ID from JWT token"""
    return event.get('requestContext', {}).get('authorizer', {}).get('claims', {}).get('sub', 'test-user-123')


def extract_user_role(event: Dict[str, Any]) -> str:
    """Extract user role from JWT token"""
    return event.get('requestContext', {}).get('authorizer', {}).get('claims', {}).get('custom:role', 'CUSTOMER')


def create_response(status_code: int, body: Dict[str, Any]) -> Dict[str, Any]:
    """Create standardized API Gateway response"""
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,Authorization',
            'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS'
        },
        'body': json.dumps(body, default=str)
    }