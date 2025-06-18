package com.myorg;

import java.util.List;
import java.util.Map;

import software.amazon.awscdk.CfnOutput;
import software.amazon.awscdk.Duration;
import software.amazon.awscdk.RemovalPolicy;
import software.amazon.awscdk.Stack;
import software.amazon.awscdk.StackProps;
import software.amazon.awscdk.services.ec2.ISecurityGroup;
import software.amazon.awscdk.services.ec2.IVpc;
import software.amazon.awscdk.services.ec2.Port;
import software.amazon.awscdk.services.ec2.SecurityGroup;
import software.amazon.awscdk.services.ec2.SubnetSelection;
import software.amazon.awscdk.services.ec2.SubnetType;
import software.amazon.awscdk.services.ecr.IRepository;
import software.amazon.awscdk.services.ecr.Repository;
import software.amazon.awscdk.services.ecs.AwsLogDriverProps;
import software.amazon.awscdk.services.ecs.Cluster;
import software.amazon.awscdk.services.ecs.ContainerDefinitionOptions;
import software.amazon.awscdk.services.ecs.ContainerImage;
import software.amazon.awscdk.services.ecs.FargateService;
import software.amazon.awscdk.services.ecs.FargateTaskDefinition;
import software.amazon.awscdk.services.ecs.LogDriver;
import software.amazon.awscdk.services.ecs.PortMapping;
import software.amazon.awscdk.services.ecs.Secret;
import software.amazon.awscdk.services.elasticloadbalancingv2.AddApplicationTargetsProps;
import software.amazon.awscdk.services.elasticloadbalancingv2.ApplicationProtocol;
import software.amazon.awscdk.services.elasticloadbalancingv2.HealthCheck;
import software.amazon.awscdk.services.elasticloadbalancingv2.IApplicationListener;
import software.amazon.awscdk.services.elasticloadbalancingv2.ListenerCondition;
import software.amazon.awscdk.services.elasticloadbalancingv2.Protocol;
import software.amazon.awscdk.services.iam.IRole;
import software.amazon.awscdk.services.iam.ManagedPolicy;
import software.amazon.awscdk.services.logs.LogGroup;
import software.amazon.awscdk.services.sqs.Queue;
import software.amazon.awscdk.services.ssm.IStringParameter;
import software.amazon.awscdk.services.ssm.StringParameter;
import software.constructs.Construct;

public class ECSFargateStack extends Stack {

	private final FargateTaskDefinition frontendTaskDef;
	private final FargateTaskDefinition backendTaskDef;
	private final FargateService frontendService;
	private final FargateService backendService;
	private final SecurityGroup backendSg;

	public ECSFargateStack(
			final Construct scope,
			final String id,
			final StackProps props,
			final IVpc vpc,
			final Queue queue,
			final IApplicationListener albHttpsListener,
			final String albFrontendDomainName,
			final String albBackendDomainName,
			final String albSecurityGroupId) {
		super(scope, id, props);

		// get the db secrets of rds postgres
		Map<String, Secret> ssmSecretsMap = getSSMParams();

		// create ECS cluster
		Cluster cluster = Cluster.Builder.create(this, "vCluster")
				.vpc(vpc)
				.build();

		cluster.applyRemovalPolicy(RemovalPolicy.DESTROY);

		// security Group for Frontend Service
		SecurityGroup frontendSg = SecurityGroup.Builder.create(this, "AngularSg")
				.vpc(vpc)
				.description("SG for Angular frontend")
				.allowAllOutbound(true)
				.build();

		ISecurityGroup albSecurityGroup = SecurityGroup.fromSecurityGroupId(this, "ImportedAlbSg", albSecurityGroupId);

		frontendSg.addIngressRule(
				albSecurityGroup,
				Port.tcp(80),
				"Allow http inbound from ALB");

		// Frontend Task Definition
		this.frontendTaskDef = FargateTaskDefinition.Builder.create(this, "FrontendTaskDef")
				.memoryLimitMiB(
						512)
				.cpu(256)
				.build();

		// Get the frontend ecr repo
		String frontendEcrRepoName = CfnStackApp.getRequiredVariable("ECR_REPO_FRONTEND");
		IRepository frontendRepo = Repository.fromRepositoryName(this, "frontend-repo", frontendEcrRepoName);

		// Explicit Log Group for Frontend with DESTROY policy
		LogGroup frontendLogGroup = LogGroup.Builder.create(this, "FrontendLogGroup")
				.removalPolicy(RemovalPolicy.DESTROY)
				.build();

		frontendTaskDef.addContainer("FrontendContainer", ContainerDefinitionOptions.builder()
				.image(ContainerImage.fromEcrRepository(frontendRepo))
				.portMappings(List.of(PortMapping.builder().containerPort(80).build()))
				.logging(LogDriver
						.awsLogs(AwsLogDriverProps.builder()
								.logGroup(frontendLogGroup)
								.streamPrefix("angular-").build()))
				// .healthCheck(software.amazon.awscdk.services.ecs.HealthCheck.builder()
				// .command(List.of("CMD-SHELL", "curl -f http://localhost/ || exit 1"))
				// .interval(Duration.seconds(30))
				// .timeout(Duration.seconds(5))
				// .retries(3)
				// .startPeriod(Duration.seconds(20))
				// .build())
				.build());

		// Frontend Fargate Service
		this.frontendService = FargateService.Builder.create(this, "FrontendService")
				.cluster(cluster)
				.taskDefinition(frontendTaskDef)
				.desiredCount(1)
				.assignPublicIp(true)
				.securityGroups(List.of(frontendSg))
				.healthCheckGracePeriod(Duration.seconds(15))
				.vpcSubnets(SubnetSelection.builder()
						.subnetType(SubnetType.PUBLIC)
						.build())
				.minHealthyPercent(100)
				.build();

		// Add Frontend Target Group to ALB Listener
		albHttpsListener.addTargets("FrontendTg", AddApplicationTargetsProps.builder()
				.port(80)
				.targets(List.of(frontendService))
				.conditions(List.of(ListenerCondition
						.hostHeaders(List.of(albFrontendDomainName))))
				.priority(1)
				.protocol(ApplicationProtocol.HTTP)
				.healthCheck(HealthCheck
						.builder()
						.path("/")
						.port("80")
						.protocol(Protocol.HTTP)
						.interval(Duration.seconds(10))
						.timeout(Duration.seconds(5))
						.healthyThresholdCount(2)
						.unhealthyThresholdCount(3)
						.build())
				.build());

		// --- Backend Service ---

		// Security Group for Backend Service
		this.backendSg = SecurityGroup.Builder.create(this, "BackendSg")
				.vpc(vpc)
				.description("SG for Backend service")
				.allowAllOutbound(true)
				.build();

		backendSg.addIngressRule(
				albSecurityGroup,
				Port.tcp(8080),
				"Allow http inbound from ALB");

		// Backend Task Definition
		this.backendTaskDef = FargateTaskDefinition.Builder.create(this, "BackendTaskDef")
				.memoryLimitMiB(512)
				.cpu(256)
				.build();

		// Get the backend ecr repos
		String backendEcrRepoName = CfnStackApp.getRequiredVariable("ECR_REPO_BACKEND");

		IRepository backendRepo = Repository.fromRepositoryName(this, "backend-repo",
				backendEcrRepoName);

		// grant backend task permission to read from secrets manager and ssm parameter
		// store
		grantEcsSqsSendMessageAccess(queue);
		grantEcsSSMReadAccess();
		grantEcsSESAccess();

		// Explicit Log Group for SpringBoot with DESTROY policy
		LogGroup backendLogGroup = LogGroup.Builder.create(this, "BackendLogGroup")
				.removalPolicy(RemovalPolicy.DESTROY)
				.build();

		backendTaskDef.addContainer("BackendContainer", ContainerDefinitionOptions.builder()
				.image(ContainerImage.fromEcrRepository(backendRepo))
				.portMappings(List.of(PortMapping.builder().containerPort(8080).build()))
				.logging(LogDriver.awsLogs(
						AwsLogDriverProps.builder()
								.logGroup(backendLogGroup)
								.streamPrefix("backend-").build()))
				// .healthCheck(software.amazon.awscdk.services.ecs.HealthCheck.builder()
				// .command(List.of("CMD-SHELL", "curl -f http://localhost:8080/health || exit
				// 1"))
				// .interval(Duration.seconds(11))
				// .timeout(Duration.seconds(2))
				// .retries(3)
				// .startPeriod(Duration.seconds(60))
				// .build())
				.environment(Map.of(
						"AWS_SQS_QUEUE_URL", queue.getQueueUrl()))
				.secrets(Map.of(
						// // // From fromSecrets Manager
						// // "SPRING_DATASOURCE_HOST", dbSecretsMap.get("host"),
						// // "SPRING_DATASOURCE_PORT", dbSecretsMap.get("port"),
						// // "SPRING_DATASOURCE_USERNAME", dbSecretsMap.get("username"),
						// // "SPRING_DATASOURCE_PASSWORD", dbSecretsMap.get("password"),
						// // "SPRING_DATASOURCE_DATABASE", dbSecretsMap.get("dbname"),
						// // From SSM Parameter Store - Use keys matching @Value annotations
						"JWT_SECRET_KEY", ssmSecretsMap.get("jwtSecret"),
						"JWT_EXPIRATION_TIME", ssmSecretsMap.get("jwtExpire"),
						"DYNAMODB_TABLE_PREFIX", ssmSecretsMap.get("ddbTablePrefix"),
						"DYNAMODB_USER_TABLE_NAME", ssmSecretsMap.get("ddbUserTableName"),
						"CORS_ALLOWED_ORIGINS", ssmSecretsMap.get("corsAllowedOrigins")))
				.build());

		// Backend Fargate Service
		this.backendService = FargateService.Builder.create(this, "BackendService")
				.cluster(cluster)
				.taskDefinition(backendTaskDef)
				.desiredCount(1)
				.assignPublicIp(true)
				.securityGroups(List.of(backendSg))
				.healthCheckGracePeriod(Duration.seconds(20))
				.vpcSubnets(SubnetSelection.builder()
						.subnetType(SubnetType.PUBLIC)
						.build())
				.minHealthyPercent(100)
				.build();

		// Add Backend Target Group to ALB Listener
		albHttpsListener.addTargets("BackendTG", AddApplicationTargetsProps.builder()
				.port(8080)
				.targets(List.of(backendService))
				.conditions(List.of(ListenerCondition
						.hostHeaders(List.of(albBackendDomainName))))
				.priority(2)
				.protocol(ApplicationProtocol.HTTP)
				.healthCheck(HealthCheck
						.builder()
						.path("/health")
						.port("8080")
						.protocol(Protocol.HTTP)
						.interval(Duration.seconds(10))
						.timeout(Duration.seconds(5))
						.healthyThresholdCount(2)
						.unhealthyThresholdCount(3)
						.build())
				.build());

		this.frontendService.applyRemovalPolicy(RemovalPolicy.DESTROY);
		this.backendService.applyRemovalPolicy(RemovalPolicy.DESTROY);
		this.frontendTaskDef.applyRemovalPolicy(RemovalPolicy.DESTROY);
		this.backendTaskDef.applyRemovalPolicy(RemovalPolicy.DESTROY);

		// outputs
		CfnOutput.Builder.create(this, "vClusterNameOutput")
				.value(cluster.getClusterName())
				.build();

		CfnOutput.Builder.create(this, "vFrontendServiceOutput")
				.value(frontendService.getServiceName())
				.build();

		CfnOutput.Builder.create(this, "vBackendServiceOutput")
				.value(backendService.getServiceName())
				.build();

	}

	public FargateService getFrontendService() {
		return frontendService;
	}

	public FargateService getBackendService() {
		return backendService;
	}

	public IRole getBackendExecutionRole() {
		return backendTaskDef.getExecutionRole();
	}

	public IRole getBackendTaskRole() {
		return backendTaskDef.getTaskRole();
	}

	public SecurityGroup getBackendSecurityGroup() {
		return backendSg;
	}

	private IStringParameter param(String id, String name) {
		return StringParameter.fromStringParameterName(this, id, name);
	}

	Map<String, Secret> getSSMParams() {

		return Map.of(
				"jwtSecret", Secret.fromSsmParameter(param("JwtSecretParam", "/restapi/JWT_SECRET_KEY")),
				"jwtExpire", Secret.fromSsmParameter(param("JwtExpireParam", "/restapi/JWT_EXPIRATION_TIME")),
				"ddbTablePrefix", Secret.fromSsmParameter(param("DdbTablePrefixParam", "/ddb/DYNAMODB_TABLE_PREFIX")),
				"ddbUserTableName",
				Secret.fromSsmParameter(param("DdbUserTableNameParam", "/ddb/DYNAMODB_USER_TABLE_NAME")),
				"corsAllowedOrigins",
				Secret.fromSsmParameter(param("CorsAllowedOriginsParam", "/restapi/CORS_ALLOWED_ORIGINS")));

	}

	public void grantEcsSSMReadAccess() {
		if (this.backendTaskDef != null && this.backendTaskDef.getExecutionRole() != null) {
			this.backendTaskDef.getExecutionRole().addManagedPolicy(
					ManagedPolicy.fromAwsManagedPolicyName("AmazonSSMReadOnlyAccess"));
		}
	}

	public void grantEcsSqsSendMessageAccess(Queue queue) {
		// Grant permission to the Task Role, which the container assumes at runtime
		if (this.backendTaskDef != null && this.backendTaskDef.getTaskRole() != null) {
			queue.grantSendMessages(this.backendTaskDef.getTaskRole());
		}
	}

	public void grantEcsSESAccess() {
		// Grant permission to the Task Role for SES email sending
		if (this.backendTaskDef != null && this.backendTaskDef.getTaskRole() != null) {
			this.backendTaskDef.getTaskRole().addManagedPolicy(
					ManagedPolicy.fromAwsManagedPolicyName("AmazonSESFullAccess"));
		}
	}

}