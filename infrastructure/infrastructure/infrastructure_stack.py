"""
AWS CDK Stack for Ticketing Platform
Deploys DynamoDB, Lambda functions, API Gateway, and Cognito authentication
"""
from aws_cdk import (
    Stack,
    Duration,
    aws_dynamodb as dynamodb,
    aws_lambda as lambda_,
    aws_apigateway as apigw,
    aws_cognito as cognito,
    aws_logs as logs,
    RemovalPolicy,
    CfnOutput
)
from constructs import Construct


class InfrastructureStack(Stack):
    """
    Main infrastructure stack for ticketing platform
    Creates DynamoDB table, Lambda functions, API Gateway, and Cognito User Pool
    """

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # ===== Cognito User Pool =====
        self.user_pool = cognito.UserPool(
            self, "TicketingUserPool",
            user_pool_name="ticketing-platform-users",
            self_sign_up_enabled=True,  # Allow users to sign up
            sign_in_aliases=cognito.SignInAliases(
                email=True,
                username=False  # Only email signin
            ),
            auto_verify=cognito.AutoVerifiedAttrs(
                email=True  # Verify email addresses
            ),
            standard_attributes=cognito.StandardAttributes(
                email=cognito.StandardAttribute(
                    required=True,
                    mutable=True
                ),
                given_name=cognito.StandardAttribute(
                    required=True,
                    mutable=True
                ),
                family_name=cognito.StandardAttribute(
                    required=True,
                    mutable=True
                )
            ),
            custom_attributes={
                "role": cognito.StringAttribute(
                    min_len=4,
                    max_len=20,
                    mutable=True
                )
            },
            password_policy=cognito.PasswordPolicy(
                min_length=8,
                require_lowercase=True,
                require_uppercase=True,
                require_digits=True,
                require_symbols=True
            ),
            account_recovery=cognito.AccountRecovery.EMAIL_ONLY,
            removal_policy=RemovalPolicy.DESTROY  # For dev environment
        )

        # User Pool Client (for web/mobile apps)
        self.user_pool_client = self.user_pool.add_client(
            "TicketingAppClient",
            user_pool_client_name="ticketing-web-client",
            auth_flows=cognito.AuthFlow(
                user_password=True,  # Username/password auth
                user_srp=True  # Secure Remote Password
            ),
            generate_secret=False,  # No secret for public clients (web/mobile)
            access_token_validity=Duration.hours(1),
            id_token_validity=Duration.hours(1),
            refresh_token_validity=Duration.days(30),
            prevent_user_existence_errors=True  # Security best practice
        )

        # ===== DynamoDB Table =====
        self.tickets_table = dynamodb.Table(
            self, "TicketsTable",
            table_name="dev-tickets",
            partition_key=dynamodb.Attribute(
                name="ticketId",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,  # For dev environment
            point_in_time_recovery=False  # Save costs in dev
        )

        # GSI-1: Query by status
        self.tickets_table.add_global_secondary_index(
            index_name="StatusIndex",
            partition_key=dynamodb.Attribute(
                name="status",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="createdAt",
                type=dynamodb.AttributeType.STRING
            ),
            projection_type=dynamodb.ProjectionType.ALL
        )

        # GSI-2: Query by assigned agent
        self.tickets_table.add_global_secondary_index(
            index_name="AssignedToIndex",
            partition_key=dynamodb.Attribute(
                name="assignedTo",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="createdAt",
                type=dynamodb.AttributeType.STRING
            ),
            projection_type=dynamodb.ProjectionType.ALL
        )

        # GSI-3: Query by creator
        self.tickets_table.add_global_secondary_index(
            index_name="CreatedByIndex",
            partition_key=dynamodb.Attribute(
                name="createdBy",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="createdAt",
                type=dynamodb.AttributeType.STRING
            ),
            projection_type=dynamodb.ProjectionType.ALL
        )

        # ===== Lambda Functions =====
        
        # Common Lambda configuration
        lambda_env = {
            "TICKETS_TABLE_NAME": self.tickets_table.table_name,
            "USER_POOL_ID": self.user_pool.user_pool_id
        }
        
        lambda_runtime = lambda_.Runtime.PYTHON_3_11
        lambda_timeout = Duration.seconds(30)
        lambda_memory = 256
        
        # Create Ticket Lambda
        self.create_ticket_fn = lambda_.Function(
            self, "CreateTicketFunction",
            function_name="create-ticket",
            runtime=lambda_runtime,
            handler="create_ticket.handler",
            code=lambda_.Code.from_asset("../backend/src/functions"),
            environment=lambda_env,
            timeout=lambda_timeout,
            memory_size=lambda_memory,
            log_retention=logs.RetentionDays.ONE_WEEK
        )
        
        # Get Ticket Lambda
        self.get_ticket_fn = lambda_.Function(
            self, "GetTicketFunction",
            function_name="get-ticket",
            runtime=lambda_runtime,
            handler="get_ticket.handler",
            code=lambda_.Code.from_asset("../backend/src/functions"),
            environment=lambda_env,
            timeout=lambda_timeout,
            memory_size=lambda_memory,
            log_retention=logs.RetentionDays.ONE_WEEK
        )
        
        # List Tickets Lambda
        self.list_tickets_fn = lambda_.Function(
            self, "ListTicketsFunction",
            function_name="list-tickets",
            runtime=lambda_runtime,
            handler="list_tickets.handler",
            code=lambda_.Code.from_asset("../backend/src/functions"),
            environment=lambda_env,
            timeout=lambda_timeout,
            memory_size=lambda_memory,
            log_retention=logs.RetentionDays.ONE_WEEK
        )
        
        # Update Ticket Lambda
        self.update_ticket_fn = lambda_.Function(
            self, "UpdateTicketFunction",
            function_name="update-ticket",
            runtime=lambda_runtime,
            handler="update_ticket.handler",
            code=lambda_.Code.from_asset("../backend/src/functions"),
            environment=lambda_env,
            timeout=lambda_timeout,
            memory_size=lambda_memory,
            log_retention=logs.RetentionDays.ONE_WEEK
        )
        
        # Delete Ticket Lambda
        self.delete_ticket_fn = lambda_.Function(
            self, "DeleteTicketFunction",
            function_name="delete-ticket",
            runtime=lambda_runtime,
            handler="delete_ticket.handler",
            code=lambda_.Code.from_asset("../backend/src/functions"),
            environment=lambda_env,
            timeout=lambda_timeout,
            memory_size=lambda_memory,
            log_retention=logs.RetentionDays.ONE_WEEK
        )
        
        # Grant DynamoDB permissions to all Lambda functions
        for fn in [self.create_ticket_fn, self.get_ticket_fn, self.list_tickets_fn, 
                   self.update_ticket_fn, self.delete_ticket_fn]:
            self.tickets_table.grant_read_write_data(fn)
        
        # Grant Cognito read permissions to Lambda functions
        for fn in [self.create_ticket_fn, self.get_ticket_fn, self.list_tickets_fn,
                   self.update_ticket_fn, self.delete_ticket_fn]:
            self.user_pool.grant(fn, "cognito-idp:AdminGetUser")
        
        # ===== API Gateway =====
        
        # Create Cognito Authorizer
        cognito_authorizer = apigw.CognitoUserPoolsAuthorizer(
            self, "TicketingAuthorizer",
            cognito_user_pools=[self.user_pool],
            identity_source="method.request.header.Authorization"
        )
        
        # Create REST API
        self.api = apigw.RestApi(
            self, "TicketingAPI",
            rest_api_name="Ticketing Platform API",
            description="REST API for ticketing platform with Cognito authentication",
            deploy_options=apigw.StageOptions(
                stage_name="dev",
                throttling_rate_limit=100,
                throttling_burst_limit=200,
                logging_level=apigw.MethodLoggingLevel.INFO,
                data_trace_enabled=True,
                metrics_enabled=True
            ),
            default_cors_preflight_options=apigw.CorsOptions(
                allow_origins=apigw.Cors.ALL_ORIGINS,
                allow_methods=apigw.Cors.ALL_METHODS,
                allow_headers=[
                    'Content-Type',
                    'Authorization',
                    'X-Amz-Date',
                    'X-Api-Key',
                    'X-Amz-Security-Token'
                ]
            )
        )
        
        # Create /tickets resource
        tickets_resource = self.api.root.add_resource("tickets")
        
        # Create /{id} resource
        ticket_id_resource = tickets_resource.add_resource("{id}")
        
        # POST /tickets → create_ticket (AUTHENTICATED)
        tickets_resource.add_method(
            "POST",
            apigw.LambdaIntegration(
                self.create_ticket_fn,
                proxy=True
            ),
            authorizer=cognito_authorizer,
            authorization_type=apigw.AuthorizationType.COGNITO
        )
        
        # GET /tickets → list_tickets (AUTHENTICATED)
        tickets_resource.add_method(
            "GET",
            apigw.LambdaIntegration(
                self.list_tickets_fn,
                proxy=True
            ),
            authorizer=cognito_authorizer,
            authorization_type=apigw.AuthorizationType.COGNITO
        )
        
        # GET /tickets/{id} → get_ticket (AUTHENTICATED)
        ticket_id_resource.add_method(
            "GET",
            apigw.LambdaIntegration(
                self.get_ticket_fn,
                proxy=True
            ),
            authorizer=cognito_authorizer,
            authorization_type=apigw.AuthorizationType.COGNITO
        )
        
        # PATCH /tickets/{id} → update_ticket (AUTHENTICATED)
        ticket_id_resource.add_method(
            "PATCH",
            apigw.LambdaIntegration(
                self.update_ticket_fn,
                proxy=True
            ),
            authorizer=cognito_authorizer,
            authorization_type=apigw.AuthorizationType.COGNITO
        )
        
        # DELETE /tickets/{id} → delete_ticket (AUTHENTICATED)
        ticket_id_resource.add_method(
            "DELETE",
            apigw.LambdaIntegration(
                self.delete_ticket_fn,
                proxy=True
            ),
            authorizer=cognito_authorizer,
            authorization_type=apigw.AuthorizationType.COGNITO
        )
        
        # ===== Outputs =====
        
        CfnOutput(
            self, "UserPoolId",
            value=self.user_pool.user_pool_id,
            description="Cognito User Pool ID",
            export_name="TicketingUserPoolId"
        )
        
        CfnOutput(
            self, "UserPoolClientId",
            value=self.user_pool_client.user_pool_client_id,
            description="Cognito User Pool Client ID",
            export_name="TicketingUserPoolClientId"
        )
        
        CfnOutput(
            self, "UserPoolArn",
            value=self.user_pool.user_pool_arn,
            description="Cognito User Pool ARN"
        )
        
        CfnOutput(
            self, "TicketsTableName",
            value=self.tickets_table.table_name,
            description="DynamoDB Tickets Table Name"
        )
        
        CfnOutput(
            self, "ApiUrl",
            value=self.api.url,
            description="API Gateway endpoint URL",
            export_name="TicketingApiUrl"
        )
        
        CfnOutput(
            self, "ApiId",
            value=self.api.rest_api_id,
            description="API Gateway ID"
        )
        
        CfnOutput(
            self, "Region",
            value=self.region,
            description="AWS Region"
        )