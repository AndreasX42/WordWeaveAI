package com.myorg;

import software.amazon.awscdk.Stack;
import software.amazon.awscdk.StackProps;
import software.constructs.Construct;

public class VocabStack extends Stack {

	public VocabStack(final Construct scope, final String id) {
		this(scope, id, null);
	}

	public VocabStack(final Construct scope, final String id, final StackProps props) {
		super(scope, id, props);

		// Ensure all nested stacks inherit the environment
		StackProps nestedStackProps = StackProps.builder().env(props.getEnv()).build();

		// create KMS customer managed key
		// KMSStack kmsStack = new KMSStack(this, "kms", nestedStackProps);

		// create shared resources (Lambda layer)
		SharedResourcesStack sharedResourcesStack = new SharedResourcesStack(this, "SharedResources", nestedStackProps);

		// create VPC
		VPCStack vpcStack = new VPCStack(this, "Vpc", nestedStackProps);

		// // create application load balancer
		// ALBStack albStack = new ALBStack(this, "Alb", nestedStackProps,
		// vpcStack.getVpc());

		// Create DataStack first for basic resources
		DataStack dataStack = new DataStack(this, "DataStack", nestedStackProps);

		// create WebSocket API (needs DataStack but not SqsLambdaStack)
		WebSocketApiStack webSocketApiStack = new WebSocketApiStack(this, "WebSocketApi", nestedStackProps,
				vpcStack.getVpc(),
				dataStack.getVocabDataTable(),
				dataStack.getConnectionsTable(),
				sharedResourcesStack.getLambdaLayer());

		// create SQS queue and lambda function with WebSocket endpoint
		SqsLambdaStack sqsLambdaStack = new SqsLambdaStack(this, "SqsLambdaStack", nestedStackProps,
				vpcStack.getVpc(), sharedResourcesStack.getLambdaLayer());

		// // create ECS Fargate cluster and services
		// ECSFargateStack ecsFargateStack = new ECSFargateStack(this, "EcsFargate",
		// nestedStackProps,
		// vpcStack.getVpc(),
		// sqsLambdaStack.getQueue(),
		// albStack.getHttpsListener(),
		// albStack.getFrontendDomainName(),
		// albStack.getBackendDomainName(),
		// albStack.getAlbSecurityGroup().getSecurityGroupId());

		// // Grant permissions to DataStack resources after all components are created
		dataStack.grantPermissions(sqsLambdaStack.getVocabProcessorLambda(), null);
		// ecsFargateStack.getBackendTaskRole());

		// // Grant WebSocket API permissions to VocabProcessorLambda
		webSocketApiStack.grantWebSocketPermissions(sqsLambdaStack.getVocabProcessorLambda());

		// create Angular CodePipeline
		// FrontendCodePipelineStack frontendCodePipelineStack = new
		// FrontendCodePipelineStack(this,
		// "FrontendPipeline",
		// nestedStackProps,
		// ecsFargateStack.getFrontendService());

		// create Backend CodePipeline
		// BackendCodePipelineStack backendCodePipelineStack = new
		// BackendCodePipelineStack(this,
		// "BackendPipeline",
		// nestedStackProps,
		// ecsFargateStack.getBackendService());
	}
}
