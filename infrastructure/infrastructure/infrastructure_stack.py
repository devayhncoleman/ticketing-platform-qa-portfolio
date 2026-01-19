from aws_cdk import (
    Stack,
    aws_dynamodb as dynamodb,
    RemovalPolicy,
    CfnOutput
)
from constructs import Construct


class InfrastructureStack(Stack):
    """
    CDK Stack for Ticketing Platform
    Creates DynamoDB table with 3 Global Secondary Indexes
    """

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create DynamoDB Tickets Table
        self.tickets_table = dynamodb.Table(
            self, "TicketsTable",
            table_name="dev-tickets",
            partition_key=dynamodb.Attribute(
                name="ticketId",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,  # For dev only!
            point_in_time_recovery=False  # Save costs in dev
        )

        # GSI-1: Query tickets by status
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

        # GSI-2: Query tickets by assigned agent
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

        # GSI-3: Query tickets by creator
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

        # Output the table name for reference
        CfnOutput(
            self, "TicketsTableName",
            value=self.tickets_table.table_name,
            description="DynamoDB Tickets Table Name",
            export_name="TicketsTableName"
        )

        CfnOutput(
            self, "TicketsTableArn",
            value=self.tickets_table.table_arn,
            description="DynamoDB Tickets Table ARN",
            export_name="TicketsTableArn"
        )