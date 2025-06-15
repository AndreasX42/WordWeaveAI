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

		// create VPC
		VPCStack vpcStack = new VPCStack(this, "Vpc", nestedStackProps);

		// // create application load balancer
		ALBStack albStack = new ALBStack(this, "Alb", nestedStackProps,
				vpcStack.getVpc());

		// create SQS queue and lambda function
		SqsLambdaStack sqsLambdaStack = new SqsLambdaStack(this, "SqsLambdaStack", nestedStackProps,
				vpcStack.getVpc());

		// // create ECS Fargate cluster and services
		ECSFargateStack ecsFargateStack = new ECSFargateStack(this, "EcsFargate",
				nestedStackProps,
				vpcStack.getVpc(),
				sqsLambdaStack.getQueue(),
				albStack.getHttpsListener(),
				albStack.getFrontendDomainName(),
				albStack.getBackendDomainName(),
				albStack.getAlbSecurityGroup().getSecurityGroupId());

		// create S3 bucket and DynamoDB tables - pass ECS task role for specific
		// permissions
		DataStack dataStack = new DataStack(this, "DataStack", nestedStackProps,
				sqsLambdaStack.getVocabProcessorLambda(),
				ecsFargateStack.getBackendTaskRole());

		// create Angular CodePipeline
		// FrontendCodePipelineStack frontendCodePipelineStack = new
		// FrontendCodePipelineStack(this,
		// "FrontendPipeline",
		// nestedStackProps,
		// ecsFargateStack.getFrontendService());

		// create Backend CodePipeline
		BackendCodePipelineStack backendCodePipelineStack = new BackendCodePipelineStack(this,
				"BackendPipeline",
				nestedStackProps,
				ecsFargateStack.getBackendService());
	}
}
