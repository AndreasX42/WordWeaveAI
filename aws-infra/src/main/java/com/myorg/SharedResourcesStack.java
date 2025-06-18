package com.myorg;

import java.util.List;

import software.amazon.awscdk.Stack;
import software.amazon.awscdk.StackProps;
import software.amazon.awscdk.services.lambda.Code;
import software.amazon.awscdk.services.lambda.LayerVersion;
import software.amazon.awscdk.services.lambda.Runtime;
import software.constructs.Construct;

public class SharedResourcesStack extends Stack {

    private final LayerVersion lambdaLayer;

    public LayerVersion getLambdaLayer() {
        return lambdaLayer;
    }

    public SharedResourcesStack(final Construct scope, final String id, final StackProps props) {
        super(scope, id, props);

        // Define the Lambda Layer that will be shared by both SqsLambdaStack and
        // WebSocketApiStack
        this.lambdaLayer = LayerVersion.Builder.create(this, "LambdaLayer")
                .layerVersionName("lambda-requirements-layer")
                .compatibleRuntimes(List.of(Runtime.PYTHON_3_11))
                .code(Code.fromAsset("resources/layers/lambda_requirements_layer.zip"))
                .build();
    }
}