package com.myorg;

import software.amazon.awscdk.Stack;
import software.amazon.awscdk.StackProps;
import software.amazon.awscdk.services.iam.IRole;
import software.constructs.Construct;

public class DataStack extends Stack {

	private final software.amazon.awscdk.services.s3.Bucket vocabBucket;
	private final software.amazon.awscdk.services.dynamodb.Table userDataTable;
	private final software.amazon.awscdk.services.dynamodb.Table vocabDataTable;
	private final software.amazon.awscdk.services.dynamodb.Table connectionsTable;

	public software.amazon.awscdk.services.s3.Bucket getVocabBucket() {
		return vocabBucket;
	}

	public software.amazon.awscdk.services.dynamodb.Table getUserDataTable() {
		return userDataTable;
	}

	public software.amazon.awscdk.services.dynamodb.Table getVocabDataTable() {
		return vocabDataTable;
	}

	public software.amazon.awscdk.services.dynamodb.Table getConnectionsTable() {
		return connectionsTable;
	}

	public DataStack(final Construct scope, final String id, final StackProps props) {
		super(scope, id, props);

		// Create S3 bucket for vocab data storage
		this.vocabBucket = software.amazon.awscdk.services.s3.Bucket.Builder.create(this, "VocabBucket")
				.bucketName(
						CfnStackApp.getRequiredVariable("S3_MEDIA_BUCKET_NAME"))
				.versioned(true)
				.publicReadAccess(false)
				.blockPublicAccess(software.amazon.awscdk.services.s3.BlockPublicAccess.BLOCK_ALL)
				.encryption(software.amazon.awscdk.services.s3.BucketEncryption.S3_MANAGED)
				.autoDeleteObjects(true)
				.removalPolicy(software.amazon.awscdk.RemovalPolicy.DESTROY)
				.build();

		// Create DynamoDB table for user data
		this.userDataTable = software.amazon.awscdk.services.dynamodb.Table.Builder
				.create(this, "UserDataTable")
				.tableName(
						CfnStackApp.getRequiredVariable("DYNAMODB_USER_TABLE_NAME"))
				.partitionKey(software.amazon.awscdk.services.dynamodb.Attribute.builder()
						.name("user_id")
						.type(software.amazon.awscdk.services.dynamodb.AttributeType.STRING)
						.build())
				.billingMode(software.amazon.awscdk.services.dynamodb.BillingMode.PAY_PER_REQUEST)
				.encryption(software.amazon.awscdk.services.dynamodb.TableEncryption.AWS_MANAGED)
				.removalPolicy(software.amazon.awscdk.RemovalPolicy.DESTROY)
				.build();

		// Add Global Secondary Indexes
		userDataTable.addGlobalSecondaryIndex(software.amazon.awscdk.services.dynamodb.GlobalSecondaryIndexProps
				.builder()
				.indexName("EmailIndex")
				.partitionKey(software.amazon.awscdk.services.dynamodb.Attribute.builder()
						.name("email")
						.type(software.amazon.awscdk.services.dynamodb.AttributeType.STRING)
						.build())
				.build());

		userDataTable.addGlobalSecondaryIndex(software.amazon.awscdk.services.dynamodb.GlobalSecondaryIndexProps
				.builder()
				.indexName("UsernameIndex")
				.partitionKey(software.amazon.awscdk.services.dynamodb.Attribute.builder()
						.name("username")
						.type(software.amazon.awscdk.services.dynamodb.AttributeType.STRING)
						.build())
				.build());

		// Create DynamoDB table for WebSocket connections
		this.connectionsTable = software.amazon.awscdk.services.dynamodb.Table.Builder
				.create(this, "ConnectionsTable")
				.tableName(CfnStackApp.getRequiredVariable("DYNAMODB_CONNECTIONS_TABLE_NAME"))
				.partitionKey(software.amazon.awscdk.services.dynamodb.Attribute.builder()
						.name("connection_id")
						.type(software.amazon.awscdk.services.dynamodb.AttributeType.STRING)
						.build())
				.timeToLiveAttribute("ttl")
				.billingMode(software.amazon.awscdk.services.dynamodb.BillingMode.PAY_PER_REQUEST)
				.encryption(software.amazon.awscdk.services.dynamodb.TableEncryption.AWS_MANAGED)
				.removalPolicy(software.amazon.awscdk.RemovalPolicy.DESTROY)
				.build();

		// Add GSI for user-based connection lookup
		connectionsTable.addGlobalSecondaryIndex(software.amazon.awscdk.services.dynamodb.GlobalSecondaryIndexProps
				.builder()
				.indexName("UserConnectionsIndex")
				.partitionKey(software.amazon.awscdk.services.dynamodb.Attribute.builder()
						.name("user_id")
						.type(software.amazon.awscdk.services.dynamodb.AttributeType.STRING)
						.build())
				.sortKey(software.amazon.awscdk.services.dynamodb.Attribute.builder()
						.name("connected_at")
						.type(software.amazon.awscdk.services.dynamodb.AttributeType.STRING)
						.build())
				.projectionType(software.amazon.awscdk.services.dynamodb.ProjectionType.ALL)
				.build());

		// Add GSI for word pair subscription-based lookup (multi-user collaborative
		// updates)
		connectionsTable.addGlobalSecondaryIndex(software.amazon.awscdk.services.dynamodb.GlobalSecondaryIndexProps
				.builder()
				.indexName("VocabWordConnectionsIndex")
				.partitionKey(software.amazon.awscdk.services.dynamodb.Attribute.builder()
						.name("vocab_word")
						.type(software.amazon.awscdk.services.dynamodb.AttributeType.STRING)
						.build())
				.projectionType(software.amazon.awscdk.services.dynamodb.ProjectionType.ALL)
				.build());

		// Create DynamoDB table for vocab data with composite key design
		this.vocabDataTable = software.amazon.awscdk.services.dynamodb.Table.Builder
				.create(this, "VocabDataTable")
				.tableName(CfnStackApp.getRequiredVariable("DYNAMODB_VOCAB_TABLE_NAME"))
				.partitionKey(software.amazon.awscdk.services.dynamodb.Attribute.builder()
						.name("PK") // Format: SRC#{lang}#{word_normalized}
						.type(software.amazon.awscdk.services.dynamodb.AttributeType.STRING)
						.build())
				.sortKey(software.amazon.awscdk.services.dynamodb.Attribute.builder()
						.name("SK") // Format: TGT#{lang}
						.type(software.amazon.awscdk.services.dynamodb.AttributeType.STRING)
						.build())
				.billingMode(software.amazon.awscdk.services.dynamodb.BillingMode.PAY_PER_REQUEST)
				.encryption(software.amazon.awscdk.services.dynamodb.TableEncryption.AWS_MANAGED)
				.pointInTimeRecoverySpecification(
						software.amazon.awscdk.services.dynamodb.PointInTimeRecoverySpecification
								.builder()
								.pointInTimeRecoveryEnabled(false)
								.build())
				.removalPolicy(software.amazon.awscdk.RemovalPolicy.DESTROY)
				.build();

		// Add GSI-1: Reverse lookup (Spanish word -> German sources)
		vocabDataTable.addGlobalSecondaryIndex(software.amazon.awscdk.services.dynamodb.GlobalSecondaryIndexProps
				.builder()
				.indexName("ReverseLookupIndex")
				.partitionKey(software.amazon.awscdk.services.dynamodb.Attribute.builder()
						.name("LKP") // Format: LKP#{target_lang}#{target_word}
						.type(software.amazon.awscdk.services.dynamodb.AttributeType.STRING)
						.build())
				.sortKey(software.amazon.awscdk.services.dynamodb.Attribute.builder()
						.name("SRC_LANG") // Format: {source_lang}
						.type(software.amazon.awscdk.services.dynamodb.AttributeType.STRING)
						.build())
				.projectionType(software.amazon.awscdk.services.dynamodb.ProjectionType.ALL)
				.build());

		// Add GSI-2: English word lookup for Media reuse
		// Use case: Given English word, find existing vocabulary entry to reuse Media
		// object
		vocabDataTable.addGlobalSecondaryIndex(software.amazon.awscdk.services.dynamodb.GlobalSecondaryIndexProps
				.builder()
				.indexName("EnglishMediaLookupIndex")
				.partitionKey(software.amazon.awscdk.services.dynamodb.Attribute.builder()
						.name("english_word") // Format: normalized English word
						.type(software.amazon.awscdk.services.dynamodb.AttributeType.STRING)
						.build())
				.projectionType(software.amazon.awscdk.services.dynamodb.ProjectionType.INCLUDE)
				.nonKeyAttributes(java.util.Arrays.asList("media", "target_word", "target_language"))
				.build());

	}

	public void grantPermissions(final software.amazon.awscdk.services.lambda.Function lambdaFunction,
			final IRole ecsTaskRole) {
		// Grant Lambda function permissions to S3 bucket and DynamoDB tables
		if (lambdaFunction != null) {
			this.vocabBucket.grantReadWrite(lambdaFunction);
			this.userDataTable.grantFullAccess(lambdaFunction);
			this.vocabDataTable.grantFullAccess(lambdaFunction);
			this.connectionsTable.grantFullAccess(lambdaFunction);
		}

		// Grant ECS task role permissions to DynamoDB tables and S3 bucket
		if (ecsTaskRole != null) {
			this.userDataTable.grantFullAccess(ecsTaskRole);
			this.vocabDataTable.grantFullAccess(ecsTaskRole);
			this.connectionsTable.grantFullAccess(ecsTaskRole);
			this.vocabBucket.grantReadWrite(ecsTaskRole);
		}
	}
}