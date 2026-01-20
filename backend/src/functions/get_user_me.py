"""
Lambda handler for getting current user's profile and role from DynamoDB
Endpoint: GET /users/me
Returns: { userId, email, role, firstName, lastName }

FILE LOCATION: backend/src/functions/get_user_me.py
"""
import json
import boto3
import os

dynamodb = boto3.resource('dynamodb')
users_table_name = os.environ.get('USERS_TABLE', 'dev-users')
users_table = dynamodb.Table(users_table_name)


def handler(event, context):
    """
    Get the current authenticated user's profile and role from DynamoDB
    Uses the Cognito 'sub' claim from the JWT token
    
    Endpoint: GET /users/me
    Response: 200 { userId, email, role, firstName, lastName }
    """
    try:
        print(f"Event: {json.dumps(event)}")
        
        # Extract user ID from authorization context
        # API Gateway Cognito authorizer puts claims in the requestContext
        claims = event.get('requestContext', {}).get('authorizer', {}).get('claims', {})
        user_id = claims.get('sub')
        
        print(f"User ID: {user_id}, Email: {claims.get('email')}")
        
        if not user_id:
            print("ERROR: No user ID found in claims")
            return error_response(401, 'Unauthorized: No user ID found')

        # Query DynamoDB users table by userId (Partition Key)
        try:
            response = users_table.get_item(Key={'userId': user_id})
            print(f"DynamoDB response: {response}")
            
            if 'Item' not in response:
                # User exists in Cognito but hasn't created a ticket yet
                # Return default CUSTOMER role with Cognito info
                print(f"User not in database, returning CUSTOMER role")
                return success_response({
                    'userId': user_id,
                    'email': claims.get('email', ''),
                    'role': 'CUSTOMER',  # Default role
                    'firstName': claims.get('given_name', ''),
                    'lastName': claims.get('family_name', '')
                })
            
            # User exists in database, return their data
            item = response['Item']
            print(f"Found user in database with role: {item.get('role')}")
            
            # Convert Decimal types to strings if needed (DynamoDB returns Decimal)
            result = {
                'userId': item.get('userId'),
                'email': item.get('email'),
                'role': item.get('role', 'CUSTOMER'),
                'firstName': item.get('firstName', ''),
                'lastName': item.get('lastName', ''),
                'createdAt': str(item.get('createdAt', ''))
            }
            
            print(f"Returning user data: {result}")
            return success_response(result)
            
        except Exception as db_error:
            print(f'Database error: {str(db_error)}')
            # If we can't query DB, return Cognito info with default role
            return success_response({
                'userId': user_id,
                'email': claims.get('email', ''),
                'role': 'CUSTOMER',
                'firstName': claims.get('given_name', ''),
                'lastName': claims.get('family_name', ''),
                'warning': 'Could not fetch full profile, using defaults'
            })
    
    except Exception as e:
        print(f'Unexpected error: {str(e)}')
        return error_response(500, f'Internal server error: {str(e)}')


def success_response(data):
    """Return successful 200 response with CORS headers"""
    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
            'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS'
        },
        'body': json.dumps(data)
    }


def error_response(status_code, message):
    """Return error response with CORS headers"""
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
            'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS'
        },
        'body': json.dumps({
            'error': message,
            'statusCode': status_code
        })
    }