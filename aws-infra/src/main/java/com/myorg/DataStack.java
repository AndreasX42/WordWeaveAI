package com.myorg;

import software.amazon.awscdk.Stack;
import software.amazon.awscdk.StackProps;
import software.amazon.awscdk.services.iam.IRole;
import software.constructs.Construct;

public class DataStack extends Stack {

	private final software.amazon.awscdk.services.s3.Bucket vocabBucket;
	private final software.amazon.awscdk.services.dynamodb.Table userDataTable;
	private final software.amazon.awscdk.services.dynamodb.Table vocabDataTable;

	public software.amazon.awscdk.services.s3.Bucket getVocabBucket() {
		return vocabBucket;
	}

	public software.amazon.awscdk.services.dynamodb.Table getUserDataTable() {
		return userDataTable;
	}

	public software.amazon.awscdk.services.dynamodb.Table getVocabDataTable() {
		return vocabDataTable;
	}

	public DataStack(final Construct scope, final String id, final StackProps props,
			final software.amazon.awscdk.services.lambda.Function lambdaFunction,
			final IRole ecsTaskRole) {
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
		// Create DynamoDB table for vocab data
		this.vocabDataTable = software.amazon.awscdk.services.dynamodb.Table.Builder
				.create(this, "VocabDataTable")
				.tableName(
						CfnStackApp.getRequiredVariable("DYNAMODB_VOCAB_TABLE_NAME"))
				.partitionKey(software.amazon.awscdk.services.dynamodb.Attribute.builder()
						.name("vocabId")
						.type(software.amazon.awscdk.services.dynamodb.AttributeType.STRING)
						.build())
				.sortKey(software.amazon.awscdk.services.dynamodb.Attribute.builder()
						.name("userId")
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

		// Grant Lambda function permissions to S3 bucket
		this.vocabBucket.grantReadWrite(lambdaFunction);

		// Grant Lambda function permissions to DynamoDB tables
		this.userDataTable.grantFullAccess(lambdaFunction);
		this.vocabDataTable.grantFullAccess(lambdaFunction);

		// Grant ECS task role permissions to DynamoDB tables and S3 bucket
		if (ecsTaskRole != null) {
			this.userDataTable.grantFullAccess(ecsTaskRole);
			this.vocabDataTable.grantFullAccess(ecsTaskRole);
			this.vocabBucket.grantReadWrite(ecsTaskRole);
		}

		// Add environment variables to Lambda function for table names and bucket name
		lambdaFunction.addEnvironment("USER_DATA_TABLE_NAME", this.userDataTable.getTableName());
		lambdaFunction.addEnvironment("VOCAB_DATA_TABLE_NAME", this.vocabDataTable.getTableName());
		lambdaFunction.addEnvironment("S3_MEDIA_BUCKET", this.vocabBucket.getBucketName());
	}
}