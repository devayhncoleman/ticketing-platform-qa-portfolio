"""
AWS CDK Stack for Ticketing Platform - Enhanced Edition
Deploys DynamoDB tables, Lambda functions, API Gateway, Cognito auth, and S3 for attachments

Features:
- Tickets with assignment to technicians
- Comments/Chat system on tickets
- Photo attachments via S3
- Role-based access (CUSTOMER, TECH, ADMIN)
"""
from aws_cdk import (
    Stack,
    Duration,
    aws_dynamodb as dynamodb,
    aws_lambda as lambda_,
    aws_apigateway as apigw,
    aws_cognito as cognito,
    aws_logs as logs,
    aws_s3 as s3,
    aws_iam as iam,
    RemovalPolicy,
    CfnOutput
)
from constructs import Construct


class InfrastructureStack(Stack):
    """
    Enhanced infrastructure stack for ticketing platform
    Now includes: Comments system, S3 attachments, role-based access
    """

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # ===== Custom Email Templates =====
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
            user_verification=cognito.UserVerificationConfig(
                email_subject="🏆 Verify your account with The Winning Team",
                email_body=verification_email_body,
                email_style=cognito.VerificationEmailStyle.CODE
            ),
            user_invitation=cognito.UserInvitationConfig(
                email_subject="🏆 Welcome to The Winning Team - {username}",
                email_body=verification_email_body.replace(
                    "verify your email address to complete your registration",
                    "Hi {username}, your admin has created an account for you. Your temporary password is: {####}"
                )
            ),
            standard_attributes=cognito.StandardAttributes(
                email=cognito.StandardAttribute(required=True, mutable=True),
                given_name=cognito.StandardAttribute(required=True, mutable=True),
                family_name=cognito.StandardAttribute(required=True, mutable=True)
            ),
            # Custom attribute for user role (CUSTOMER, TECH, ADMIN)
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
                user_srp=True,
                admin_user_password=True  # Allow admin to set passwords
            ),
            generate_secret=False,
            access_token_validity=Duration.hours(1),
            id_token_validity=Duration.hours(1),
            refresh_token_validity=Duration.days(30),
            prevent_user_existence_errors=True
            # Note: Custom attribute read/write is handled by default
            # when the attribute is defined as mutable
        )

        # ===== S3 Bucket for Attachments =====
        self.attachments_bucket = s3.Bucket(
            self, "AttachmentsBucket",
            bucket_name=f"ticketing-attachments-{self.account}-{self.region}",
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,  # For dev - deletes objects when bucket is deleted
            # Security settings
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
            # CORS for frontend uploads
            cors=[s3.CorsRule(
                allowed_methods=[s3.HttpMethods.GET, s3.HttpMethods.PUT, s3.HttpMethods.POST],
                allowed_origins=["*"],  # In production, restrict to your domain
                allowed_headers=["*"],
                max_age=3000
            )],
            # Lifecycle rule - delete attachments after 12 months (matching ticket retention)
            lifecycle_rules=[
                s3.LifecycleRule(
                    id="DeleteAfter12Months",
                    expiration=Duration.days(365),
                    enabled=True
                )
            ]
        )

        # ===== DynamoDB Tables =====

        # Table 1: Tickets (enhanced with assignment)
        self.tickets_table = dynamodb.Table(
            self, "TicketsTable",
            table_name="dev-tickets",
            partition_key=dynamodb.Attribute(
                name="ticketId",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
            point_in_time_recovery=False,
            # TTL for auto-deletion after 12 months (set on closed tickets)
            time_to_live_attribute="ttl"
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

        # GSI-2: Query by creator (customer's tickets)
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

        # NOTE: AssignedToIndex will be added in a future deployment
        # DynamoDB only allows one GSI change per deployment
        # For now, we'll query assigned tickets by scanning with a filter
        # Uncomment below after the initial deployment succeeds:
        #
        # self.tickets_table.add_global_secondary_index(
        #     index_name="AssignedToIndex",
        #     partition_key=dynamodb.Attribute(
        #         name="assignedTo",
        #         type=dynamodb.AttributeType.STRING
        #     ),
        #     sort_key=dynamodb.Attribute(
        #         name="createdAt",
        #         type=dynamodb.AttributeType.STRING
        #     )
        # )

        # Table 2: Comments/Messages (for ticket chat)
        self.comments_table = dynamodb.Table(
            self, "CommentsTable",
            table_name="dev-ticket-comments",
            partition_key=dynamodb.Attribute(
                name="ticketId",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="commentId",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
            time_to_live_attribute="ttl"  # Auto-delete with ticket
        )

        # Table 3: Users (for role management and tech directory)
        self.users_table = dynamodb.Table(
            self, "UsersTable",
            table_name="dev-users",
            partition_key=dynamodb.Attribute(
                name="userId",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY
        )

        # GSI for users by role (list all techs, all admins)
        self.users_table.add_global_secondary_index(
            index_name="RoleIndex",
            partition_key=dynamodb.Attribute(
                name="role",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="createdAt",
                type=dynamodb.AttributeType.STRING
            )
        )

        # GSI for users by email (lookup)
        self.users_table.add_global_secondary_index(
            index_name="EmailIndex",
            partition_key=dynamodb.Attribute(
                name="email",
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
                "TICKETS_TABLE": self.tickets_table.table_name,
                "COMMENTS_TABLE": self.comments_table.table_name,
                "USERS_TABLE": self.users_table.table_name,
                "ATTACHMENTS_BUCKET": self.attachments_bucket.bucket_name,
                "USER_POOL_ID": self.user_pool.user_pool_id
            }
        }

        # ----- Ticket Functions -----
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

        self.assign_ticket_fn = lambda_.Function(
            self, "AssignTicketFunction",
            function_name="assign-ticket",
            handler="handler.assign_ticket",
            code=lambda_.Code.from_asset("../backend/src"),
            **lambda_defaults
        )

        # ----- Comment Functions -----
        self.create_comment_fn = lambda_.Function(
            self, "CreateCommentFunction",
            function_name="create-comment",
            handler="handler.create_comment",
            code=lambda_.Code.from_asset("../backend/src"),
            **lambda_defaults
        )

        self.list_comments_fn = lambda_.Function(
            self, "ListCommentsFunction",
            function_name="list-comments",
            handler="handler.list_comments",
            code=lambda_.Code.from_asset("../backend/src"),
            **lambda_defaults
        )

        # ----- Attachment Functions -----
        self.get_upload_url_fn = lambda_.Function(
            self, "GetUploadUrlFunction",
            function_name="get-upload-url",
            handler="handler.get_upload_url",
            code=lambda_.Code.from_asset("../backend/src"),
            **lambda_defaults
        )

        # ----- User/Admin Functions -----
        self.list_users_fn = lambda_.Function(
            self, "ListUsersFunction",
            function_name="list-users",
            handler="handler.list_users",
            code=lambda_.Code.from_asset("../backend/src"),
            **lambda_defaults
        )

        self.update_user_role_fn = lambda_.Function(
            self, "UpdateUserRoleFunction",
            function_name="update-user-role",
            handler="handler.update_user_role",
            code=lambda_.Code.from_asset("../backend/src"),
            **lambda_defaults
        )

        self.get_technicians_fn = lambda_.Function(
            self, "GetTechniciansFunction",
            function_name="get-technicians",
            handler="handler.get_technicians",
            code=lambda_.Code.from_asset("../backend/src"),
            **lambda_defaults
        )

        # ----- Get Current User Function -----
        self.get_user_me_fn = lambda_.Function(
            self, "GetUserMeFunction",
            function_name="get-user-me",
            handler="handler.get_user_me",
            code=lambda_.Code.from_asset("../backend/src"),
            **lambda_defaults
        )

        # ===== Permissions =====
        # 
        # TICKET FUNCTIONS
        # - create_ticket: needs tickets (write), users (write for sync)
        # - get_ticket: needs tickets (read)
        # - list_tickets: needs tickets (read), users (read for role check)
        # - update_ticket: needs tickets (read/write)
        # - delete_ticket: needs tickets (read/write)
        # - assign_ticket: needs tickets (read/write), users (read to verify tech)
        #
        # COMMENT FUNCTIONS
        # - create_comment: needs comments (write), tickets (read for ownership check), users (read for role)
        # - list_comments: needs comments (read), tickets (read for ownership check), users (read for role)
        #
        # USER FUNCTIONS
        # - list_users: needs users (read), cognito (list)
        # - update_user_role: needs users (read/write), cognito (admin update)
        # - get_technicians: needs users (read)

        # ----- Ticket Function Permissions -----
        self.tickets_table.grant_read_write_data(self.create_ticket_fn)
        self.users_table.grant_read_write_data(self.create_ticket_fn)  # Sync user on first ticket

        self.tickets_table.grant_read_data(self.get_ticket_fn)

        self.tickets_table.grant_read_data(self.list_tickets_fn)
        self.users_table.grant_read_data(self.list_tickets_fn)  # Check user role

        self.tickets_table.grant_read_write_data(self.update_ticket_fn)
        self.users_table.grant_read_data(self.update_ticket_fn)  # Check user role

        self.tickets_table.grant_read_write_data(self.delete_ticket_fn)
        self.users_table.grant_read_data(self.delete_ticket_fn)  # Check user role

        self.tickets_table.grant_read_write_data(self.assign_ticket_fn)
        self.users_table.grant_read_data(self.assign_ticket_fn)  # Verify tech exists

        # ----- Comment Function Permissions -----
        self.comments_table.grant_read_write_data(self.create_comment_fn)
        self.tickets_table.grant_read_write_data(self.create_comment_fn)  # Verify ownership + update lastCommentAt
        self.users_table.grant_read_data(self.create_comment_fn)  # Get user role for internal notes

        self.comments_table.grant_read_data(self.list_comments_fn)
        self.tickets_table.grant_read_data(self.list_comments_fn)  # Verify ticket ownership
        self.users_table.grant_read_data(self.list_comments_fn)  # Get user role to filter internal notes

        # ----- Attachment Function Permissions -----
        self.attachments_bucket.grant_put(self.get_upload_url_fn)
        self.attachments_bucket.grant_read(self.get_ticket_fn)
        self.attachments_bucket.grant_read(self.list_comments_fn)

        # ----- User/Admin Function Permissions -----
        self.users_table.grant_read_data(self.list_users_fn)
        self.users_table.grant_read_write_data(self.update_user_role_fn)
        self.users_table.grant_read_data(self.get_technicians_fn)
        self.users_table.grant_read_data(self.get_user_me_fn)  # Read user role for get-user-me

        # Cognito permissions for admin functions
        self.update_user_role_fn.add_to_role_policy(
            iam.PolicyStatement(
                actions=[
                    "cognito-idp:AdminUpdateUserAttributes",
                    "cognito-idp:AdminGetUser",
                    "cognito-idp:ListUsers"
                ],
                resources=[self.user_pool.user_pool_arn]
            )
        )

        self.list_users_fn.add_to_role_policy(
            iam.PolicyStatement(
                actions=["cognito-idp:ListUsers"],
                resources=[self.user_pool.user_pool_arn]
            )
        )

        # ===== API Gateway =====
        self.api = apigw.RestApi(
            self, "TicketingAPI",
            rest_api_name="Ticketing API",
            description="API for ticketing platform with comments and attachments",
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

        # ----- Ticket Endpoints -----
        tickets_resource = self.api.root.add_resource("tickets")
        single_ticket_resource = tickets_resource.add_resource("{id}")

        # POST /tickets - Create ticket
        tickets_resource.add_method(
            "POST",
            apigw.LambdaIntegration(self.create_ticket_fn),
            authorizer=authorizer,
            authorization_type=apigw.AuthorizationType.COGNITO
        )

        # GET /tickets - List tickets
        tickets_resource.add_method(
            "GET",
            apigw.LambdaIntegration(self.list_tickets_fn),
            authorizer=authorizer,
            authorization_type=apigw.AuthorizationType.COGNITO
        )

        # GET /tickets/{id} - Get single ticket
        single_ticket_resource.add_method(
            "GET",
            apigw.LambdaIntegration(self.get_ticket_fn),
            authorizer=authorizer,
            authorization_type=apigw.AuthorizationType.COGNITO
        )

        # PATCH /tickets/{id} - Update ticket (status only, no content editing)
        single_ticket_resource.add_method(
            "PATCH",
            apigw.LambdaIntegration(self.update_ticket_fn),
            authorizer=authorizer,
            authorization_type=apigw.AuthorizationType.COGNITO
        )

        # DELETE /tickets/{id} - Delete ticket (CLOSED only, soft delete)
        single_ticket_resource.add_method(
            "DELETE",
            apigw.LambdaIntegration(self.delete_ticket_fn),
            authorizer=authorizer,
            authorization_type=apigw.AuthorizationType.COGNITO
        )

        # POST /tickets/{id}/assign - Assign ticket to tech (ADMIN only)
        assign_resource = single_ticket_resource.add_resource("assign")
        assign_resource.add_method(
            "POST",
            apigw.LambdaIntegration(self.assign_ticket_fn),
            authorizer=authorizer,
            authorization_type=apigw.AuthorizationType.COGNITO
        )

        # ----- Comment Endpoints -----
        comments_resource = single_ticket_resource.add_resource("comments")

        # POST /tickets/{id}/comments - Add comment
        comments_resource.add_method(
            "POST",
            apigw.LambdaIntegration(self.create_comment_fn),
            authorizer=authorizer,
            authorization_type=apigw.AuthorizationType.COGNITO
        )

        # GET /tickets/{id}/comments - List comments
        comments_resource.add_method(
            "GET",
            apigw.LambdaIntegration(self.list_comments_fn),
            authorizer=authorizer,
            authorization_type=apigw.AuthorizationType.COGNITO
        )

        # ----- Attachment Endpoints -----
        attachments_resource = self.api.root.add_resource("attachments")
        upload_url_resource = attachments_resource.add_resource("upload-url")

        # POST /attachments/upload-url - Get presigned URL for upload
        upload_url_resource.add_method(
            "POST",
            apigw.LambdaIntegration(self.get_upload_url_fn),
            authorizer=authorizer,
            authorization_type=apigw.AuthorizationType.COGNITO
        )

        # ----- User/Admin Endpoints -----
        users_resource = self.api.root.add_resource("users")
        single_user_resource = users_resource.add_resource("{userId}")
        technicians_resource = self.api.root.add_resource("technicians")

        # GET /users - List all users (ADMIN only)
        users_resource.add_method(
            "GET",
            apigw.LambdaIntegration(self.list_users_fn),
            authorizer=authorizer,
            authorization_type=apigw.AuthorizationType.COGNITO
        )

        # PATCH /users/{userId}/role - Update user role (ADMIN only)
        role_resource = single_user_resource.add_resource("role")
        role_resource.add_method(
            "PATCH",
            apigw.LambdaIntegration(self.update_user_role_fn),
            authorizer=authorizer,
            authorization_type=apigw.AuthorizationType.COGNITO
        )

        # GET /technicians - List all techs (for assignment dropdown)
        technicians_resource.add_method(
            "GET",
            apigw.LambdaIntegration(self.get_technicians_fn),
            authorizer=authorizer,
            authorization_type=apigw.AuthorizationType.COGNITO
        )

        # GET /users/me - Get current user's profile and role
        me_resource = users_resource.add_resource("me")
        me_resource.add_method(
            "GET",
            apigw.LambdaIntegration(self.get_user_me_fn),
            authorizer=authorizer,
            authorization_type=apigw.AuthorizationType.COGNITO
        )

        # ===== Outputs =====
        CfnOutput(self, "ApiId", value=self.api.rest_api_id)
        CfnOutput(self, "ApiUrl", value=self.api.url)
        CfnOutput(self, "Region", value=self.region)
        CfnOutput(self, "TicketingAPIEndpoint", value=self.api.url, description="API Gateway endpoint URL")
        CfnOutput(self, "TicketsTableName", value=self.tickets_table.table_name)
        CfnOutput(self, "CommentsTableName", value=self.comments_table.table_name)
        CfnOutput(self, "UsersTableName", value=self.users_table.table_name)
        CfnOutput(self, "AttachmentsBucketName", value=self.attachments_bucket.bucket_name)
        CfnOutput(self, "UserPoolArn", value=self.user_pool.user_pool_arn)
        CfnOutput(self, "UserPoolClientId", value=self.user_pool_client.user_pool_client_id)
        CfnOutput(self, "UserPoolId", value=self.user_pool.user_pool_id)