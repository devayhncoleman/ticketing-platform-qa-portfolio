"""
Lambda handler for listing tickets with filters and pagination
Updated: Uses Cognito JWT for real user authentication and role-based filtering
"""
import json
import os
import base64
from typing import Dict, Any, Optional
import boto3
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key, Attr

# Import auth utilities
from auth import extract_user_from_event, UserContext

# Initialize DynamoDB
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
table_name = os.environ.get('TICKETS_TABLE_NAME', 'dev-tickets')
table = dynamodb.Table(table_name)


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for GET /tickets
    Lists tickets with optional filters, pagination, and role-based access
    
    Query Parameters:
        - status: Filter by status (uses StatusIndex GSI)
        - assignedTo: Filter by assigned agent (uses AssignedToIndex GSI)
        - limit: Max items per page (default 20, max 100)
        - cursor: Pagination token for next page
        
    Authorization:
        - ADMIN/AGENT: Can see all tickets
        - CUSTOMER: Can only see their own tickets
    """
    try:
        # Extract authenticated user from Cognito JWT
        user = extract_user_from_event(event)
        
        # Parse query parameters
        params = event.get('queryStringParameters') or {}
        status_filter = params.get('status')
        assigned_to_filter = params.get('assignedTo')
        
        # Pagination
        limit = min(int(params.get('limit', 20)), 100)
        cursor = params.get('cursor')
        
        # Decode cursor if provided
        exclusive_start_key = None
        if cursor:
            try:
                decoded = base64.b64decode(cursor).decode('utf-8')
                exclusive_start_key = json.loads(decoded)
            except Exception as e:
                print(f"Invalid cursor: {e}")
                return create_response(400, {'error': 'Invalid pagination cursor'})
        
        # Build scan/query parameters
        scan_kwargs = {
            'Limit': limit
        }
        
        if exclusive_start_key:
            scan_kwargs['ExclusiveStartKey'] = exclusive_start_key
        
        # Role-based filtering
        if user.is_customer:
            # Customers can only see their own tickets - use CreatedByIndex
            scan_kwargs['IndexName'] = 'CreatedByIndex'
            scan_kwargs['KeyConditionExpression'] = Key('createdBy').eq(user.user_id)
            
            # Add status filter if provided
            if status_filter:
                scan_kwargs['FilterExpression'] = Attr('status').eq(status_filter.upper())
            
            response = table.query(**scan_kwargs)
        
        elif status_filter:
            # Use StatusIndex GSI for status filtering
            scan_kwargs['IndexName'] = 'StatusIndex'
            scan_kwargs['KeyConditionExpression'] = Key('status').eq(status_filter.upper())
            response = table.query(**scan_kwargs)
        
        elif assigned_to_filter:
            # Use AssignedToIndex GSI for assigned agent filtering
            scan_kwargs['IndexName'] = 'AssignedToIndex'
            scan_kwargs['KeyConditionExpression'] = Key('assignedTo').eq(assigned_to_filter)
            response = table.query(**scan_kwargs)
        
        else:
            # Full table scan (admins/agents with no filters)
            response = table.scan(**scan_kwargs)
        
        tickets = response.get('Items', [])
        
        # Build response with pagination
        result = {
            'tickets': tickets,
            'count': len(tickets)
        }
        
        # Add next cursor if more results exist
        if 'LastEvaluatedKey' in response:
            next_cursor = base64.b64encode(
                json.dumps(response['LastEvaluatedKey']).encode('utf-8')
            ).decode('utf-8')
            result['nextCursor'] = next_cursor
            result['hasMore'] = True
        else:
            result['hasMore'] = False
        
        print(f"User {user.email} (role: {user.role}) listed {len(tickets)} tickets")
        return create_response(200, result)
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        print(f"DynamoDB error: {error_code} - {e}")
        return create_response(500, {'error': 'Failed to list tickets'})
        
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return create_response(500, {'error': 'Internal server error'})


def create_response(status_code: int, body: Dict[str, Any]) -> Dict[str, Any]:
    """Create standardized API Gateway response."""
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