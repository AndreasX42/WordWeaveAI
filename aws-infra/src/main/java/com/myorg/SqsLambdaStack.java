package com.myorg;

import java.util.List;
import java.util.Map;

import software.amazon.awscdk.Duration;
import software.amazon.awscdk.Stack;
import software.amazon.awscdk.StackProps;
import software.amazon.awscdk.services.ec2.IVpc;
import software.amazon.awscdk.services.ec2.SecurityGroup;
import software.amazon.awscdk.services.iam.ManagedPolicy;
import software.amazon.awscdk.services.lambda.Architecture;
import software.amazon.awscdk.services.lambda.Code;
import software.amazon.awscdk.services.lambda.Function;
import software.amazon.awscdk.services.lambda.LayerVersion;
import software.amazon.awscdk.services.lambda.Runtime;
import software.amazon.awscdk.services.lambda.eventsources.SqsEventSource;
import software.amazon.awscdk.services.sqs.DeadLetterQueue;
import software.amazon.awscdk.services.sqs.Queue;
import software.amazon.awscdk.services.sqs.QueueEncryption;
import software.amazon.awscdk.services.ssm.StringParameter;
import software.constructs.Construct;

public class SqsLambdaStack extends Stack {

	private final Queue queue;
	private final Queue deadLetterQueue;
	private final SecurityGroup lambdaSecurityGroup;
	private final Function vocabProcessorLambda;

	public Queue getQueue() {
		return queue;
	}

	public Queue getDeadLetterQueue() {
		return deadLetterQueue;
	}

	public SecurityGroup getLambdaSecurityGroup() {
		return lambdaSecurityGroup;
	}

	public Function getVocabProcessorLambda() {
		return vocabProcessorLambda;
	}

	public SqsLambdaStack(final Construct scope, final String id, final StackProps props,
			final IVpc vpc, final LayerVersion lambdaLayer) {
		super(scope, id, props);

		// Create Dead Letter Queue first
		this.deadLetterQueue = Queue.Builder.create(this, "VocabJobsDeadLetterQueue")
				.queueName("vocab-jobs-dlq.fifo")
				.fifo(true)
				.encryption(QueueEncryption.SQS_MANAGED)
				.build();

		// Define the main queue with DLQ configuration
		this.queue = Queue.Builder.create(this, "VocabJobsQueue")
				.queueName("vocab-jobs-queue.fifo")
				.fifo(true)
				.visibilityTimeout(Duration.seconds(150))
				.encryption(QueueEncryption.SQS_MANAGED)
				.deadLetterQueue(DeadLetterQueue.builder()
						.queue(this.deadLetterQueue)
						.maxReceiveCount(1)
						.build())
				.build();

		// Create a Security Group for the Lambda function
		this.lambdaSecurityGroup = SecurityGroup.Builder.create(this, "LambdaSg")
				.vpc(vpc)
				.description("Security group for Vocab Lambda")
				.allowAllOutbound(true)
				.build();

		// Retrieve SSM parameter values at deployment time
		String openaiApiKey = StringParameter.valueForStringParameter(this, "/apikeys/DEFAULT_OPENAI_API_KEY");
		String pexelsApiKey = StringParameter.valueForStringParameter(this, "/apikeys/PEXELS_API_KEY");
		String elevenLabsApiKey = StringParameter.valueForStringParameter(this, "/apikeys/ELEVENLABS_API_KEY");

		// define the Lambda Function
		this.vocabProcessorLambda = Function.Builder.create(this, "VocabProcessorLambda")
				.runtime(Runtime.PYTHON_3_12)
				.handler("lambda_handler.lambda_handler")
				.code(Code.fromAsset("resources/lambda/vocab_processor_zip.zip"))
				.memorySize(256)
				.timeout(Duration.seconds(120))
				.layers(List.of(lambdaLayer))
				.architecture(Architecture.ARM_64)
				.environment(Map.of(
						"OPENAI_API_KEY", openaiApiKey,
						"PEXELS_API_KEY", pexelsApiKey,
						"ELEVENLABS_API_KEY", elevenLabsApiKey,
						"AGENT_EXECUTION_CONTEXT", "lambda",
						"DYNAMODB_USER_TABLE_NAME",
						CfnStackApp.getRequiredVariable("DYNAMODB_USER_TABLE_NAME"),
						"DYNAMODB_VOCAB_TABLE_NAME",
						CfnStackApp.getRequiredVariable("DYNAMODB_VOCAB_TABLE_NAME"),
						"DYNAMODB_VOCAB_MEDIA_TABLE_NAME",
						CfnStackApp.getRequiredVariable("DYNAMODB_VOCAB_MEDIA_TABLE_NAME"),
						"DYNAMODB_CONNECTIONS_TABLE_NAME",
						CfnStackApp.getRequiredVariable("DYNAMODB_CONNECTIONS_TABLE_NAME"),
						"S3_MEDIA_BUCKET_NAME", CfnStackApp.getRequiredVariable("S3_MEDIA_BUCKET_NAME")))
				// .vpc(vpc)
				// .vpcSubnets(SubnetSelection.builder()
				// .subnetType(SubnetType.PUBLIC)
				// .build())
				// .securityGroups(List.of(this.lambdaSecurityGroup))
				.build();

		// Grant sqs permissions
		queue.grantConsumeMessages(this.vocabProcessorLambda);

		// Attach the AmazonSSMReadOnlyAccess managed policy
		this.vocabProcessorLambda.getRole().addManagedPolicy(
				ManagedPolicy.fromAwsManagedPolicyName("AmazonSSMReadOnlyAccess"));

		// Add SQS trigger
		this.vocabProcessorLambda.addEventSource(new SqsEventSource(queue));
		// Add VPC endpoint access managed policy
		// this.vocabProcessorLambda.getRole().addManagedPolicy(
		// ManagedPolicy.fromAwsManagedPolicyName("service-role/AWSLambdaVPCAccessExecutionRole"));

		// Add SQS trigger with batch size optimization
		// this.vocabProcessorLambda.addEventSource(new SqsEventSource(queue,
		// SqsEventSourceProps.builder()
		// .batchSize(10) // Process up to 10 messages at once
		// .maxBatchingWindow(Duration.seconds(5)) // Wait up to 5 seconds to batch
		// messages
		// .build()));
	}
}
