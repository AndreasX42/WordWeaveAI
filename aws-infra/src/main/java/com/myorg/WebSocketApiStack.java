package com.myorg;

import java.util.List;
import java.util.Map;

import software.amazon.awscdk.Duration;
import software.amazon.awscdk.Stack;
import software.amazon.awscdk.StackProps;
import software.amazon.awscdk.aws_apigatewayv2_integrations.WebSocketLambdaIntegration;
import software.amazon.awscdk.services.apigatewayv2.WebSocketApi;
import software.amazon.awscdk.services.apigatewayv2.WebSocketRoute;
import software.amazon.awscdk.services.apigatewayv2.WebSocketStage;
import software.amazon.awscdk.services.dynamodb.ITable;
import software.amazon.awscdk.services.ec2.IVpc;
import software.amazon.awscdk.services.iam.Effect;
import software.amazon.awscdk.services.iam.PolicyStatement;
import software.amazon.awscdk.services.lambda.Architecture;
import software.amazon.awscdk.services.lambda.Code;
import software.amazon.awscdk.services.lambda.Function;
import software.amazon.awscdk.services.lambda.LayerVersion;
import software.amazon.awscdk.services.lambda.Runtime;
import software.constructs.Construct;

public class WebSocketApiStack extends Stack {

	private final WebSocketApi webSocketApi;
	private final Function connectHandler;
	private final Function disconnectHandler;
	private final Function defaultHandler;
	// private final SecurityGroup webSocketLambdaSecurityGroup;
	private String websocketEndpoint;

	public WebSocketApi getWebSocketApi() {
		return webSocketApi;
	}

	public String getWebSocketEndpoint() {
		return websocketEndpoint;
	}

	public Function getConnectHandler() {
		return connectHandler;
	}

	public Function getDisconnectHandler() {
		return disconnectHandler;
	}

	public Function getDefaultHandler() {
		return defaultHandler;
	}

	// public SecurityGroup getWebSocketLambdaSecurityGroup() {
	// return webSocketLambdaSecurityGroup;
	// }

	public void grantWebSocketPermissions(Function externalFunction) {
		PolicyStatement apiGatewayPolicy = PolicyStatement.Builder.create()
				.effect(Effect.ALLOW)
				.actions(List.of("execute-api:ManageConnections"))
				.resources(List.of(
						String.format("arn:aws:execute-api:%s:%s:%s/*",
								this.getRegion(), this.getAccount(),
								webSocketApi.getApiId())))
				.build();

		externalFunction.addToRolePolicy(apiGatewayPolicy);
		externalFunction.addEnvironment("WEBSOCKET_API_ENDPOINT", this.websocketEndpoint);
	}

	public WebSocketApiStack(final Construct scope, final String id, final StackProps props,
			final IVpc vpc, final ITable vocabTable, final ITable connectionsTable,
			final LayerVersion layer) {
		super(scope, id, props);

		// Create security group for WebSocket Lambda functions
		// this.webSocketLambdaSecurityGroup = SecurityGroup.Builder.create(this,
		// "WebSocketLambdaSg")
		// .vpc(vpc)
		// .description("Security group for WebSocket Lambda functions")
		// .allowAllOutbound(true)
		// .build();

		// Create WebSocket API
		this.webSocketApi = WebSocketApi.Builder.create(this, "VocabWebSocketApi")
				.apiName("vocab-processor-websocket")
				.description("WebSocket API for real-time vocab processing updates")
				.build();

		// Shared Lambda configuration for consistency
		Map<String, String> commonEnvironment = Map.of(
				"DYNAMODB_CONNECTIONS_TABLE_NAME", connectionsTable.getTableName()
		// "DYNAMODB_VOCAB_TABLE_NAME", vocabTable.getTableName(),
		// "AWS_NODEJS_CONNECTION_REUSE_ENABLED", "1")
		);

		// Create Connect Lambda Handler
		this.connectHandler = Function.Builder.create(this, "WebSocketConnectHandler")
				.runtime(Runtime.PYTHON_3_12)
				.handler("websocket_handler.connect_handler")
				.code(Code.fromAsset("resources/lambda/websocket_handler_zip.zip"))
				.memorySize(128)
				.timeout(Duration.seconds(30))
				.layers(List.of(layer))
				.architecture(Architecture.ARM_64)
				// .vpc(vpc) // Enable VPC for better security
				// .vpcSubnets(SubnetSelection.builder()
				// .subnetType(SubnetType.PRIVATE_WITH_EGRESS)
				// .build())
				// .securityGroups(List.of(webSocketLambdaSecurityGroup))
				.environment(commonEnvironment)
				.build();

		// Create Disconnect Lambda Handler
		this.disconnectHandler = Function.Builder.create(this, "WebSocketDisconnectHandler")
				.runtime(Runtime.PYTHON_3_12)
				.handler("websocket_handler.disconnect_handler")
				.code(Code.fromAsset("resources/lambda/websocket_handler_zip.zip"))
				.memorySize(128)
				.timeout(Duration.seconds(30))
				.layers(List.of(layer))
				.architecture(Architecture.ARM_64)
				// .vpc(vpc) // Enable VPC for better security
				// .vpcSubnets(SubnetSelection.builder()
				// .subnetType(SubnetType.PRIVATE_WITH_EGRESS)
				// .build())
				// .securityGroups(List.of(webSocketLambdaSecurityGroup))
				.environment(commonEnvironment)
				.build();

		// Create Default Lambda Handler (for unknown routes)
		this.defaultHandler = Function.Builder.create(this, "WebSocketDefaultHandler")
				.runtime(Runtime.PYTHON_3_12)
				.handler("websocket_handler.default_handler")
				.code(Code.fromAsset("resources/lambda/websocket_handler_zip.zip"))
				.memorySize(128)
				.timeout(Duration.seconds(30))
				.layers(List.of(layer))
				.architecture(Architecture.ARM_64)
				// .vpc(vpc)
				// .vpcSubnets(SubnetSelection.builder()
				// .subnetType(SubnetType.PRIVATE_WITH_EGRESS)
				// .build())
				// .securityGroups(List.of(webSocketLambdaSecurityGroup))
				.environment(commonEnvironment)
				.build();

		// Grant DynamoDB permissions to all handlers
		connectionsTable.grantReadWriteData(this.connectHandler);
		connectionsTable.grantReadWriteData(this.disconnectHandler);
		connectionsTable.grantReadWriteData(this.defaultHandler);

		// Grant VPC access permissions for all Lambda functions
		// List<Function> allWebSocketFunctions = List.of(connectHandler,
		// disconnectHandler, defaultHandler);
		// for (Function function : allWebSocketFunctions) {
		// function.getRole().addManagedPolicy(
		// ManagedPolicy.fromAwsManagedPolicyName("service-role/AWSLambdaVPCAccessExecutionRole"));
		// }

		// Grant API Gateway management permissions for sending messages
		PolicyStatement apiGatewayPolicy = PolicyStatement.Builder.create()
				.effect(Effect.ALLOW)
				.actions(List.of("execute-api:ManageConnections"))
				.resources(List.of(
						String.format("arn:aws:execute-api:%s:%s:%s/*",
								this.getRegion(), this.getAccount(),
								webSocketApi.getApiId())))
				.build();

		this.connectHandler.addToRolePolicy(apiGatewayPolicy);
		this.disconnectHandler.addToRolePolicy(apiGatewayPolicy);
		this.defaultHandler.addToRolePolicy(apiGatewayPolicy);

		// Create WebSocket routes
		WebSocketRoute connectRoute = WebSocketRoute.Builder.create(this, "ConnectRoute")
				.webSocketApi(this.webSocketApi)
				.routeKey("$connect")
				.integration(new WebSocketLambdaIntegration("ConnectIntegration", this.connectHandler))
				.build();

		WebSocketRoute disconnectRoute = WebSocketRoute.Builder.create(this, "DisconnectRoute")
				.webSocketApi(this.webSocketApi)
				.routeKey("$disconnect")
				.integration(new WebSocketLambdaIntegration("DisconnectIntegration",
						this.disconnectHandler))
				.build();

		WebSocketRoute defaultRoute = WebSocketRoute.Builder.create(this, "DefaultRoute")
				.webSocketApi(this.webSocketApi)
				.routeKey("$default")
				.integration(new WebSocketLambdaIntegration("DefaultIntegration", this.defaultHandler))
				.build();

		// Create WebSocket stage
		WebSocketStage stage = WebSocketStage.Builder.create(this, "ProductionStage")
				.webSocketApi(this.webSocketApi)
				.stageName("prod")
				.autoDeploy(true)
				.throttle(software.amazon.awscdk.services.apigatewayv2.ThrottleSettings.builder()
						.rateLimit(100)
						.burstLimit(50)
						.build())
				.build();

		// Add WebSocket endpoint to all Lambda functions
		this.websocketEndpoint = String.format("https://%s.execute-api.%s.amazonaws.com/prod",
				this.webSocketApi.getApiId(), this.getRegion());

		this.connectHandler.addEnvironment("WEBSOCKET_API_ENDPOINT", this.websocketEndpoint);
		this.disconnectHandler.addEnvironment("WEBSOCKET_API_ENDPOINT", this.websocketEndpoint);
		this.defaultHandler.addEnvironment("WEBSOCKET_API_ENDPOINT", this.websocketEndpoint);
	}
}