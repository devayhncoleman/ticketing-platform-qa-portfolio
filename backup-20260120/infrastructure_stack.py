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

        # ===== Custom Email Templates =====
        # Verification email template (for new user signup)
        verification_email_body = """
<div style="background-color: #0d0d1a; padding: 40px 20px; font-family: 'Courier New', monospace;">
  <div style="max-width: 500px; margin: 0 auto; background-color: #1a1a2e; border: 1px solid rgba(0, 255, 65, 0.3); border-radius: 8px; overflow: hidden;">
    <div style="text-align: center; padding: 30px 20px; border-bottom: 1px solid rgba(0, 255, 65, 0.2);">
      <div style="font-size: 48px; margin-bottom: 10px;">🏆</div>
      <h1 style="color: #00ff41; font-size: 24px; margin: 0; letter-spacing: 2px;">THE_WINNING_TEAM</h1>
      <p style="color: #888; font-size: 12px; margin-top: 8px;">>_ Precision Support Portal</p>
    </div>
    <div style="padding: 30px; color: #e0e0e0;">
      <p style="color: #00ff41; font-size: 14px; margin-bottom: 20px;">// auth.verify()</p>
      <p style="margin-bottom: 20px;">Welcome to The Winning Team!<br/>Please verify your email address to complete your registration.</p>
      <div style="background-color: #0d0d1a; border: 1px solid rgba(0, 255, 65, 0.3); border-radius: 6px; padding: 20px; text-align: center; margin: 25px 0;">
        <p style="color: #888; font-size: 12px; margin-bottom: 10px;">YOUR VERIFICATION CODE</p>
        <p style="color: #00ff41; font-size: 32px; letter-spacing: 8px; margin: 0; font-weight: bold;">{####}</p>
      </div>
      <p style="color: #888; font-size: 12px;">This code expires in 24 hours. If you didn't create an account with The Winning Team, please ignore this email.</p>
    </div>
    <div style="text-align: center; padding: 20px; border-top: 1px solid rgba(0, 255, 65, 0.2); color: #666; font-size: 11px;">
      © 2026 The Winning Team • Precision Support Portal
    </div>
  </div>
</div>
"""

        # ===== Cognito User Pool =====
        self.user_pool = cognito.UserPool(
            self, "TicketingUserPool",
            user_pool_name="ticketing-platform-users",
            self_sign_up_enabled=True,
            sign_in_aliases=cognito.SignInAliases(
                email=True,
                username=False
            ),
            auto_verify=cognito.AutoVerifiedAttrs(
                email=True
            ),
            # Custom email settings for verification
            user_verification=cognito.UserVerificationConfig(
                email_subject="🏆 Verify your account with The Winning Team",
                email_body=verification_email_body,
                email_style=cognito.VerificationEmailStyle.CODE
            ),
            # Custom invitation email
            user_invitation=cognito.UserInvitationConfig(
                email_subject="🏆 Welcome to The Winning Team",
                email_body=verification_email_body.replace(
                    "verify your email address to complete your registration",
                    "Your admin has created an account for you. Your temporary password is: {####}"
                )
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
            removal_policy=RemovalPolicy.DESTROY
        )

        # User Pool Client
        self.user_pool_client = self.user_pool.add_client(
            "TicketingAppClient",
            user_pool_client_name="ticketing-web-client",
            auth_flows=cognito.AuthFlow(
                user_password=True,
                user_srp=True
            ),
            generate_secret=False,
            access_token_validity=Duration.hours(1),
            id_token_validity=Duration.hours(1),
            refresh_token_validity=Duration.days(30),
            prevent_user_existence_errors=True
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
            removal_policy=RemovalPolicy.DESTROY,
            point_in_time_recovery=False
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
            )
        )

        # GSI-2: Query by user
        self.tickets_table.add_global_secondary_index(
            index_name="UserIndex",
            partition_key=dynamodb.Attribute(
                name="createdBy",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="createdAt",
                type=dynamodb.AttributeType.STRING
            )
        )

        # ===== Lambda Functions =====
        lambda_defaults = {
            "runtime": lambda_.Runtime.PYTHON_3_11,
            "timeout": Duration.seconds(30),
            "memory_size": 256,
            "log_retention": logs.RetentionDays.ONE_WEEK,
            "environment": {
                "TABLE_NAME": self.tickets_table.table_name,
                "USER_POOL_ID": self.user_pool.user_pool_id
            }
        }

        self.create_ticket_fn = lambda_.Function(
            self, "CreateTicketFunction",
            function_name="create-ticket",
            handler="handler.create_ticket",
            code=lambda_.Code.from_asset("../backend/src"),
            **lambda_defaults
        )

        self.get_ticket_fn = lambda_.Function(
            self, "GetTicketFunction",
            function_name="get-ticket",
            handler="handler.get_ticket",
            code=lambda_.Code.from_asset("../backend/src"),
            **lambda_defaults
        )

        self.list_tickets_fn = lambda_.Function(
            self, "ListTicketsFunction",
            function_name="list-tickets",
            handler="handler.list_tickets",
            code=lambda_.Code.from_asset("../backend/src"),
            **lambda_defaults
        )

        self.update_ticket_fn = lambda_.Function(
            self, "UpdateTicketFunction",
            function_name="update-ticket",
            handler="handler.update_ticket",
            code=lambda_.Code.from_asset("../backend/src"),
            **lambda_defaults
        )

        self.delete_ticket_fn = lambda_.Function(
            self, "DeleteTicketFunction",
            function_name="delete-ticket",
            handler="handler.delete_ticket",
            code=lambda_.Code.from_asset("../backend/src"),
            **lambda_defaults
        )

        # Grant DynamoDB permissions
        self.tickets_table.grant_read_write_data(self.create_ticket_fn)
        self.tickets_table.grant_read_data(self.get_ticket_fn)
        self.tickets_table.grant_read_data(self.list_tickets_fn)
        self.tickets_table.grant_read_write_data(self.update_ticket_fn)
        self.tickets_table.grant_read_write_data(self.delete_ticket_fn)

        # ===== API Gateway =====
        self.api = apigw.RestApi(
            self, "TicketingAPI",
            rest_api_name="Ticketing API",
            description="API for ticketing platform",
            deploy_options=apigw.StageOptions(
                stage_name="dev",
                logging_level=apigw.MethodLoggingLevel.INFO,
                data_trace_enabled=True,
                throttling_rate_limit=100,
                throttling_burst_limit=50
            ),
            default_cors_preflight_options=apigw.CorsOptions(
                allow_origins=apigw.Cors.ALL_ORIGINS,
                allow_methods=apigw.Cors.ALL_METHODS,
                allow_headers=["Content-Type", "Authorization", "X-Amz-Date", "X-Api-Key"],
                allow_credentials=True
            )
        )

        authorizer = apigw.CognitoUserPoolsAuthorizer(
            self, "TicketingAuthorizer",
            cognito_user_pools=[self.user_pool],
            authorizer_name="cognito-authorizer",
            identity_source="method.request.header.Authorization"
        )

        tickets_resource = self.api.root.add_resource("tickets")
        single_ticket_resource = tickets_resource.add_resource("{id}")

        tickets_resource.add_method(
            "POST",
            apigw.LambdaIntegration(self.create_ticket_fn),
            authorizer=authorizer,
            authorization_type=apigw.AuthorizationType.COGNITO
        )

        tickets_resource.add_method(
            "GET",
            apigw.LambdaIntegration(self.list_tickets_fn),
            authorizer=authorizer,
            authorization_type=apigw.AuthorizationType.COGNITO
        )

        single_ticket_resource.add_method(
            "GET",
            apigw.LambdaIntegration(self.get_ticket_fn),
            authorizer=authorizer,
            authorization_type=apigw.AuthorizationType.COGNITO
        )

        single_ticket_resource.add_method(
            "PATCH",
            apigw.LambdaIntegration(self.update_ticket_fn),
            authorizer=authorizer,
            authorization_type=apigw.AuthorizationType.COGNITO
        )

        single_ticket_resource.add_method(
            "DELETE",
            apigw.LambdaIntegration(self.delete_ticket_fn),
            authorizer=authorizer,
            authorization_type=apigw.AuthorizationType.COGNITO
        )

        # ===== Outputs =====
        CfnOutput(self, "ApiId", value=self.api.rest_api_id)
        CfnOutput(self, "ApiUrl", value=self.api.url)
        CfnOutput(self, "Region", value=self.region)
        CfnOutput(
            self, "TicketingAPIEndpoint",
            value=f"{self.api.url}",
            description="API Gateway endpoint URL"
        )
        CfnOutput(
            self, "TicketsTableName",
            value=self.tickets_table.table_name
        )
        CfnOutput(
            self, "UserPoolArn",
            value=self.user_pool.user_pool_arn
        )
        CfnOutput(
            self, "UserPoolClientId",
            value=self.user_pool_client.user_pool_client_id
        )
        CfnOutput(
            self, "UserPoolId",
            value=self.user_pool.user_pool_id
        )