package com.myorg;

import java.util.List;
import java.util.Map;

import software.amazon.awscdk.Duration;
import software.amazon.awscdk.Stack;
import software.amazon.awscdk.StackProps;
import software.amazon.awscdk.services.ec2.IVpc;
import software.amazon.awscdk.services.ec2.SecurityGroup;
import software.amazon.awscdk.services.ec2.SubnetSelection;
import software.amazon.awscdk.services.ec2.SubnetType;
import software.amazon.awscdk.services.iam.ManagedPolicy;
import software.amazon.awscdk.services.lambda.Code;
import software.amazon.awscdk.services.lambda.Function;
import software.amazon.awscdk.services.lambda.LayerVersion;
import software.amazon.awscdk.services.lambda.Runtime;
import software.amazon.awscdk.services.lambda.eventsources.SqsEventSource;
import software.amazon.awscdk.services.sqs.Queue;
import software.amazon.awscdk.services.ssm.StringParameter;
import software.constructs.Construct;

public class SqsLambdaStack extends Stack {

	private final Queue queue;
	private final SecurityGroup lambdaSecurityGroup;
	private final Function vocabProcessorLambda;

	public Queue getQueue() {
		return queue;
	}

	public SecurityGroup getLambdaSecurityGroup() {
		return lambdaSecurityGroup;
	}

	public Function getVocabProcessorLambda() {
		return vocabProcessorLambda;
	}

	public SqsLambdaStack(final Construct scope, final String id, final StackProps props,
			final IVpc vpc) {
		super(scope, id, props);

		// define the queue
		this.queue = Queue.Builder.create(this, "VocabJobsQueue")
				.queueName("vocab-jobs-queue.fifo")
				.visibilityTimeout(Duration.seconds(150))
				.fifo(true)
				.build();

		// define the Lambda Layer
		LayerVersion layer = LayerVersion.Builder.create(this, "LambdaLayer")
				.layerVersionName("lambda-requirements-layer")
				.compatibleRuntimes(List.of(Runtime.PYTHON_3_11))
				.code(Code.fromAsset("resources/layers/lambda_requirements_layer.zip"))
				.build();

		// Create a Security Group for the Lambda function
		this.lambdaSecurityGroup = SecurityGroup.Builder.create(this, "LambdaSg")
				.vpc(vpc)
				.description("Security group for Vocab Lambda")
				.allowAllOutbound(true)
				.build();

		// Retrieve SSM parameter values at deployment time
		String openaiApiKey = StringParameter.valueForStringParameter(this, "/apikeys/DEFAULT_OPENAI_API_KEY");

		// define the Lambda Function
		this.vocabProcessorLambda = Function.Builder.create(this, "VocabProcessorLambda")
				.runtime(Runtime.PYTHON_3_11)
				.handler("vocab_processor.lambda_handler.lambda_handler")
				.code(Code.fromAsset("resources/lambda/vocab_processor_zip.zip"))
				.memorySize(256)
				.timeout(Duration.seconds(120))
				.layers(List.of(layer))
				.environment(Map.of(
						"DEFAULT_OPENAI_API_KEY", openaiApiKey))
				.vpc(vpc)
				.vpcSubnets(SubnetSelection.builder()
						.subnetType(SubnetType.PRIVATE_ISOLATED)
						.build())
				.securityGroups(List.of(this.lambdaSecurityGroup))
				.build();

		// Grant sqs permissions
		queue.grantConsumeMessages(this.vocabProcessorLambda);

		// Attach the AmazonSSMReadOnlyAccess managed policy
		this.vocabProcessorLambda.getRole().addManagedPolicy(
				ManagedPolicy.fromAwsManagedPolicyName("AmazonSSMReadOnlyAccess"));

		// Add SQS trigger
		this.vocabProcessorLambda.addEventSource(new SqsEventSource(queue));
	}
}
