package com.myorg;

import software.amazon.awscdk.Stack;
import software.amazon.awscdk.StackProps;
import software.amazon.awscdk.services.codebuild.*;
import software.amazon.awscdk.services.codepipeline.Artifact;
import software.amazon.awscdk.services.codepipeline.Pipeline;
import software.amazon.awscdk.services.codepipeline.StageProps;
import software.amazon.awscdk.services.codepipeline.actions.CodeBuildAction;
import software.amazon.awscdk.services.codepipeline.actions.EcsDeployAction;
import software.amazon.awscdk.services.codepipeline.actions.ManualApprovalAction;
import software.amazon.awscdk.services.ecr.IRepository;
import software.amazon.awscdk.services.ecr.Repository;
import software.amazon.awscdk.services.ecs.IBaseService;
import software.constructs.Construct;
import software.amazon.awscdk.services.codepipeline.actions.CodeStarConnectionsSourceAction;
import software.amazon.awscdk.services.iam.ManagedPolicy;

import java.util.Arrays;
import java.util.Map;
import java.util.List;
import software.amazon.awscdk.Duration;
import software.amazon.awscdk.services.logs.LogGroup;
import software.amazon.awscdk.services.logs.RetentionDays;
import software.amazon.awscdk.services.codebuild.LoggingOptions;
import software.amazon.awscdk.services.codebuild.CloudWatchLoggingOptions;
import software.amazon.awscdk.RemovalPolicy;

public class BackendCodePipelineStack extends Stack {

    public BackendCodePipelineStack(
            final Construct scope,
            final String id,
            final StackProps props,
            final IBaseService backendService) {
        super(scope, id, props);

        // --- Source Stage ---

        // Import the backend ECR repositories
        String springbootEcrRepoName = CfnStackApp.getRequiredVariable("ECR_REPO_SPRINGBOOT");
        IRepository springbootRepo = Repository.fromRepositoryName(this, "SpringbootRepo",
                springbootEcrRepoName);

        // Define the source artifact
        Artifact sourceOutput = new Artifact("SourceOutput");

        // GitHub Source Action using CodeStar Connection ARN
        String githubConnectionArn = CfnStackApp.getRequiredVariable("GITHUB_CONNECTION_ARN");
        String githubOwner = CfnStackApp.getRequiredVariable("GITHUB_OWNER");
        String githubRepo = CfnStackApp.getRequiredVariable("GITHUB_REPO_BACKEND");
        String githubBranch = CfnStackApp.getRequiredVariable("GITHUB_BRANCH");

        CodeStarConnectionsSourceAction sourceAction = CodeStarConnectionsSourceAction.Builder.create()
                .actionName("GitHub_Source")
                .owner(githubOwner)
                .repo(githubRepo)
                .branch(githubBranch)
                .connectionArn(githubConnectionArn)
                .output(sourceOutput)
                .build();

        // --- Build Stage ---

        // Define the CodeBuild project
        PipelineProject buildProject = PipelineProject.Builder.create(this, "BackendBuildProject")
                .projectName("BackendBuild")
                .environment(BuildEnvironment.builder()
                        .buildImage(LinuxBuildImage.AMAZON_LINUX_2023_5)
                        .privileged(true)
                        .build())
                .logging(LoggingOptions.builder()
                        .cloudWatch(CloudWatchLoggingOptions.builder()
                                .logGroup(LogGroup.Builder
                                        .create(this, "BackendBuildLogGroup")
                                        .logGroupName("/aws/codebuild/BackendBuild")
                                        .retention(RetentionDays.ONE_DAY)
                                        .removalPolicy(RemovalPolicy.DESTROY)
                                        .build())
                                .build())
                        .build())
                .buildSpec(BuildSpec.fromSourceFilename(".aws/buildspec.yaml"))
                .environmentVariables(Map.of(
                        "ECR_SB_REPO_NAME", BuildEnvironmentVariable.builder()
                                .value(springbootRepo.getRepositoryUri())
                                .build(),
                        "AWS_REGION", BuildEnvironmentVariable.builder()
                                .value(Stack.of(this).getRegion())
                                .build(),
                        "AWS_ACCOUNT_ID", BuildEnvironmentVariable.builder()
                                .value(Stack.of(this).getAccount())
                                .build()))
                .build();

        // Grant CodeBuild project permission to push to the ECR repositories
        springbootRepo.grantPullPush(buildProject.getRole());

        // Grant CodeBuild project permission to read SSM parameters
        buildProject.getRole().addManagedPolicy(
                ManagedPolicy.fromAwsManagedPolicyName("AmazonSSMReadOnlyAccess"));

        // Define the build artifact
        Artifact buildOutput = new Artifact("BuildOutput");

        CodeBuildAction buildAction = CodeBuildAction.Builder.create()
                .actionName("Build")
                .project(buildProject)
                .input(sourceOutput)
                .outputs(List.of(buildOutput))
                .build();

        // --- Deploy Stage ---

        // ECS Deploy Action for the backend service
        EcsDeployAction deployAction = EcsDeployAction.Builder.create()
                .actionName("Deploy_to_ECS")
                .service(backendService)
                .deploymentTimeout(Duration.minutes(10))
                .input(buildOutput)
                .build();

        // --- Approval Stage ---
        ManualApprovalAction manualApprovalAction = ManualApprovalAction.Builder.create()
                .actionName("Manual_Approval")
                .runOrder(1)
                .build();

        // --- Pipeline Definition ---
        Pipeline.Builder.create(this, "BackendPipeline")
                .pipelineName("BackendPipeline")
                .stages(Arrays.asList(
                        StageProps.builder()
                                .stageName("Source")
                                .actions(List.of(sourceAction))
                                .build(),
                        StageProps.builder()
                                .stageName("Approve")
                                .actions(List.of(manualApprovalAction))
                                .build(),
                        StageProps.builder()
                                .stageName("Build")
                                .actions(List.of(buildAction))
                                .build(),
                        StageProps.builder()
                                .stageName("Deploy")
                                .actions(List.of(deployAction))
                                .build()))
                .build();
    }
}