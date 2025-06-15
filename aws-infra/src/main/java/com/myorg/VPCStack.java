package com.myorg;

import java.util.Arrays;
import java.util.List;

import software.amazon.awscdk.Stack;
import software.amazon.awscdk.StackProps;
import software.amazon.awscdk.services.ec2.GatewayVpcEndpointAwsService;
import software.amazon.awscdk.services.ec2.GatewayVpcEndpointOptions;
import software.amazon.awscdk.services.ec2.InterfaceVpcEndpointAwsService;
import software.amazon.awscdk.services.ec2.InterfaceVpcEndpointOptions;
import software.amazon.awscdk.services.ec2.Peer;
import software.amazon.awscdk.services.ec2.Port;
import software.amazon.awscdk.services.ec2.SecurityGroup;
import software.amazon.awscdk.services.ec2.SubnetConfiguration;
import software.amazon.awscdk.services.ec2.SubnetSelection;
import software.amazon.awscdk.services.ec2.SubnetType;
import software.amazon.awscdk.services.ec2.Vpc;
import software.amazon.awscdk.services.ec2.VpcProps;
import software.constructs.Construct;

public class VPCStack extends Stack {
	private final Vpc vpc;

	public Vpc getVpc() {
		return vpc;
	}

	public VPCStack(final Construct scope, final String id) {
		this(scope, id, null);
	}

	public VPCStack(final Construct scope, final String id, final StackProps props) {
		super(scope, id, props);

		this.vpc = new Vpc(this, "vVpc", VpcProps.builder()
				.maxAzs(2)
				.natGateways(0)
				.subnetConfiguration(Arrays.asList(
						SubnetConfiguration.builder()
								.name("vPublicSubnet")
								.subnetType(SubnetType.PUBLIC)
								.cidrMask(24)
								.build(),
						// SubnetConfiguration.builder()
						// .name("vPrivateEgressSubnet")
						// .subnetType(SubnetType.PRIVATE_WITH_EGRESS)
						// .cidrMask(24)
						// .build(),
						SubnetConfiguration.builder()
								.name("vPrivateIsolatedSubnet")
								.subnetType(SubnetType.PRIVATE_ISOLATED)
								.cidrMask(24)
								.build()))
				.build());

		// create a dedicated Security Group for VPC Endpoints ***
		SecurityGroup endpointSg = SecurityGroup.Builder.create(this, "EndpointSecurityGroup")
				.vpc(vpc)
				.description("SG for VPC Interface Endpoints")
				.allowAllOutbound(false)
				.build();

		// Allow traffic from within the VPC to the endpoints on HTTPS port
		endpointSg.addIngressRule(
				Peer.ipv4(vpc.getVpcCidrBlock()),
				Port.tcp(443),
				"Allow HTTPS traffic from within VPC to Endpoints");

		// Create a SubnetSelection for the private subnets
		SubnetSelection privateSubnetSelection = SubnetSelection.builder()
				.subnetType(SubnetType.PRIVATE_ISOLATED)
				.build();

		// Add S3 Gateway Endpoint (no SG applicable)
		vpc.addGatewayEndpoint("S3Endpoint", GatewayVpcEndpointOptions.builder()
				.service(GatewayVpcEndpointAwsService.S3)
				.subnets(List.of(privateSubnetSelection))
				.build());

		// Add DynamoDB Gateway Endpoint (no SG applicable)
		vpc.addGatewayEndpoint("DynamoDbEndpoint", GatewayVpcEndpointOptions.builder()
				.service(GatewayVpcEndpointAwsService.DYNAMODB)
				.subnets(List.of(privateSubnetSelection))
				.build());

		// Add Interface Endpoints to the private subnets using the dedicated SG
		vpc.addInterfaceEndpoint("EcrApiEndpoint", InterfaceVpcEndpointOptions.builder()
				.service(InterfaceVpcEndpointAwsService.ECR)
				.privateDnsEnabled(true)
				.subnets(privateSubnetSelection)
				.securityGroups(List.of(endpointSg))
				.build());

		vpc.addInterfaceEndpoint("EcrDkrEndpoint", InterfaceVpcEndpointOptions.builder()
				.service(InterfaceVpcEndpointAwsService.ECR_DOCKER)
				.privateDnsEnabled(true)
				.subnets(privateSubnetSelection)
				.securityGroups(List.of(endpointSg)) // Use shared SG
				.build());

		vpc.addInterfaceEndpoint("CloudWatchLogsEndpoint", InterfaceVpcEndpointOptions.builder()
				.service(InterfaceVpcEndpointAwsService.CLOUDWATCH_LOGS)
				.privateDnsEnabled(true)
				.subnets(privateSubnetSelection)
				.securityGroups(List.of(endpointSg)) // Use shared SG
				.build());

		vpc.addInterfaceEndpoint("EcsEndpoint", InterfaceVpcEndpointOptions.builder()
				.service(InterfaceVpcEndpointAwsService.ECS)
				.privateDnsEnabled(true)
				.subnets(privateSubnetSelection)
				.securityGroups(List.of(endpointSg)) // Use shared SG
				.build());

		vpc.addInterfaceEndpoint("EcsAgentEndpoint", InterfaceVpcEndpointOptions.builder()
				.service(InterfaceVpcEndpointAwsService.ECS_AGENT)
				.privateDnsEnabled(true)
				.subnets(privateSubnetSelection)
				.securityGroups(List.of(endpointSg)) // Use shared SG
				.build());

		vpc.addInterfaceEndpoint("EcsTelemetryEndpoint", InterfaceVpcEndpointOptions.builder()
				.service(InterfaceVpcEndpointAwsService.ECS_TELEMETRY)
				.privateDnsEnabled(true)
				.subnets(privateSubnetSelection)
				.securityGroups(List.of(endpointSg)) // Use shared SG
				.build());

		// Add SSM Interface Endpoint
		vpc.addInterfaceEndpoint("SsmEndpoint", InterfaceVpcEndpointOptions.builder()
				.service(InterfaceVpcEndpointAwsService.SSM)
				.privateDnsEnabled(true)
				.subnets(privateSubnetSelection)
				.securityGroups(List.of(endpointSg)) // Use shared SG
				.build());

		// Add SQS Interface Endpoint
		vpc.addInterfaceEndpoint("SqsEndpoint", InterfaceVpcEndpointOptions.builder()
				.service(InterfaceVpcEndpointAwsService.SQS)
				.privateDnsEnabled(true)
				.subnets(privateSubnetSelection)
				.securityGroups(List.of(endpointSg))
				.build());

		// Add SES Interface Endpoint
		vpc.addInterfaceEndpoint("SesEndpoint", InterfaceVpcEndpointOptions.builder()
				.service(InterfaceVpcEndpointAwsService.EMAIL_SMTP)
				.privateDnsEnabled(true)
				.subnets(privateSubnetSelection)
				.securityGroups(List.of(endpointSg))
				.build());
	}
}
