# S3 Bucket for Pipeline Artifacts
resource "aws_s3_bucket" "pipeline_artifacts" {
  bucket        = "${var.project_name}-${var.target_environment}-pipeline-artifacts"
  force_destroy = true

  tags = {
    Name        = "${var.project_name}-${var.target_environment}-pipeline-artifacts"
    Environment = var.environment
    TargetEnv   = var.target_environment
    Project     = var.project_name
  }
}

resource "aws_s3_bucket_versioning" "pipeline_artifacts" {
  bucket = aws_s3_bucket.pipeline_artifacts.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "pipeline_artifacts" {
  bucket = aws_s3_bucket.pipeline_artifacts.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "pipeline_artifacts" {
  bucket = aws_s3_bucket.pipeline_artifacts.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# IAM Role for CodePipeline
resource "aws_iam_role" "codepipeline_role" {
  name = "${var.project_name}-${var.target_environment}-codepipeline-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "codepipeline.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name        = "${var.project_name}-${var.target_environment}-codepipeline-role"
    Environment = var.environment
    TargetEnv   = var.target_environment
    Project     = var.project_name
  }
}

resource "aws_iam_role_policy" "codepipeline_policy" {
  name = "${var.project_name}-codepipeline-policy"
  role = aws_iam_role.codepipeline_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetBucketVersioning",
          "s3:GetObject",
          "s3:GetObjectVersion",
          "s3:PutObject",
          "s3:PutObjectAcl"
        ]
        Resource = [
          aws_s3_bucket.pipeline_artifacts.arn,
          "${aws_s3_bucket.pipeline_artifacts.arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "codebuild:BatchGetBuilds",
          "codebuild:StartBuild"
        ]
        Resource = [
          aws_codebuild_project.frontend.arn,
          aws_codebuild_project.backend.arn
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "ecs:DescribeServices",
          "ecs:DescribeTaskDefinition",
          "ecs:DescribeTasks",
          "ecs:ListTasks",
          "ecs:RegisterTaskDefinition",
          "ecs:UpdateService",
          "ecs:DescribeClusters",
          "ecs:ListServices",
          "ecs:ListTaskDefinitions",
          "ecs:DescribeContainerInstances",
          "ecs:ListContainerInstances",
          "ecs:CreateService",
          "ecs:DeleteService",
          "ecs:RunTask",
          "ecs:StartTask",
          "ecs:StopTask",
          "ecs:TagResource",
          "ecs:UntagResource",
          "ecs:DescribeCapacityProviders",
          "ecs:ListTagsForResource"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "application-autoscaling:DescribeScalableTargets",
          "application-autoscaling:DescribeScalingPolicies",
          "application-autoscaling:RegisterScalableTarget",
          "application-autoscaling:DeregisterScalableTarget"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "iam:PassRole"
        ]
        Resource = [
          var.ecs_frontend_task_execution_role_arn,
          var.ecs_backend_task_execution_role_arn,
          var.ecs_frontend_task_role_arn,
          var.ecs_backend_task_role_arn
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "codeconnections:UseConnection",
          "codeconnections:GetConnection",
          "codestar-connections:UseConnection",
          "codestar-connections:GetConnection"
        ]
        Resource = [
          var.github_connection_arn,
          "arn:aws:codestar-connections:*:*:connection/*",
          "arn:aws:codeconnections:*:*:connection/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "*"
      }
    ]
  })
}

# IAM Role for CodeBuild
resource "aws_iam_role" "codebuild_role" {
  name = "${var.project_name}-${var.target_environment}-codebuild-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "codebuild.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name        = "${var.project_name}-${var.target_environment}-codebuild-role"
    Environment = var.environment
    TargetEnv   = var.target_environment
    Project     = var.project_name
  }
}

resource "aws_iam_role_policy" "codebuild_policy" {
  name = "${var.project_name}-codebuild-policy"
  role = aws_iam_role.codebuild_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:${var.aws_region}:${var.aws_account_id}:log-group:/aws/codebuild/*"
      },
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:GetObjectVersion",
          "s3:PutObject"
        ]
        Resource = [
          aws_s3_bucket.pipeline_artifacts.arn,
          "${aws_s3_bucket.pipeline_artifacts.arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "ecr:BatchCheckLayerAvailability",
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage",
          "ecr:GetAuthorizationToken",
          "ecr:InitiateLayerUpload",
          "ecr:UploadLayerPart",
          "ecr:CompleteLayerUpload",
          "ecr:PutImage"
        ]
        Resource = "*"
      }
    ]
  })
}

# CodeBuild Project for Frontend
resource "aws_codebuild_project" "frontend" {
  name         = "${var.project_name}-${var.target_environment}-frontend-build"
  description  = "Build project for frontend"
  service_role = aws_iam_role.codebuild_role.arn

  artifacts {
    type = "CODEPIPELINE"
  }

  environment {
    compute_type                = "BUILD_GENERAL1_SMALL"
    image                       = "aws/codebuild/amazonlinux-aarch64-standard:3.0"
    type                        = "ARM_CONTAINER"
    image_pull_credentials_type = "CODEBUILD"
    privileged_mode             = true

    environment_variable {
      name  = "AWS_DEFAULT_REGION"
      value = var.aws_region
    }

    environment_variable {
      name  = "AWS_ACCOUNT_ID"
      value = var.aws_account_id
    }

    environment_variable {
      name  = "ECR_REPO_FRONTEND"
      value = "${var.aws_account_id}.dkr.ecr.${var.aws_region}.amazonaws.com/${var.frontend_ecr_repo_name}"
    }

    environment_variable {
      name  = "ECS_TASK_EXECUTION_ROLE_ARN"
      value = var.ecs_frontend_task_execution_role_arn
    }

    environment_variable {
      name  = "ECS_TASK_ROLE_ARN"
      value = var.ecs_frontend_task_role_arn
    }

    environment_variable {
      name  = "BASE_URL"
      value = "https://${var.backend_domain_name}/api"
    }

    environment_variable {
      name  = "WEBSOCKET_URL"
      value = replace(var.websocket_api_endpoint, "https://", "wss://")
    }
  }

  source {
    type      = "CODEPIPELINE"
    buildspec = "frontend/.aws/buildspec.yaml"
  }

  logs_config {
    cloudwatch_logs {
      group_name = aws_cloudwatch_log_group.codebuild_frontend.name
    }
  }

  tags = {
    Name        = "${var.project_name}-${var.target_environment}-frontend-build"
    Environment = var.environment
    TargetEnv   = var.target_environment
    Project     = var.project_name
  }
}

# CodeBuild Project for Backend
resource "aws_codebuild_project" "backend" {
  name         = "${var.project_name}-${var.target_environment}-backend-build"
  description  = "Build project for backend"
  service_role = aws_iam_role.codebuild_role.arn

  artifacts {
    type = "CODEPIPELINE"
  }

  environment {
    compute_type                = "BUILD_GENERAL1_SMALL"
    image                       = "aws/codebuild/amazonlinux-aarch64-standard:3.0"
    type                        = "ARM_CONTAINER"
    image_pull_credentials_type = "CODEBUILD"
    privileged_mode             = true

    environment_variable {
      name  = "AWS_DEFAULT_REGION"
      value = var.aws_region
    }

    environment_variable {
      name  = "AWS_ACCOUNT_ID"
      value = var.aws_account_id
    }

    environment_variable {
      name  = "ECR_REPO_BACKEND"
      value = "${var.aws_account_id}.dkr.ecr.${var.aws_region}.amazonaws.com/${var.backend_ecr_repo_name}"
    }

    environment_variable {
      name  = "ECS_TASK_EXECUTION_ROLE_ARN"
      value = var.ecs_backend_task_execution_role_arn
    }

    environment_variable {
      name  = "ECS_TASK_ROLE_ARN"
      value = var.ecs_backend_task_role_arn
    }
  }

  source {
    type      = "CODEPIPELINE"
    buildspec = "restapi/.aws/buildspec.yaml"
  }

  logs_config {
    cloudwatch_logs {
      group_name = aws_cloudwatch_log_group.codebuild_backend.name
    }
  }

  tags = {
    Name        = "${var.project_name}-${var.target_environment}-backend-build"
    Environment = var.environment
    TargetEnv   = var.target_environment
    Project     = var.project_name
  }
}

# CloudWatch Log Groups for CodeBuild
resource "aws_cloudwatch_log_group" "codebuild_frontend" {
  name              = "/aws/codebuild/${var.project_name}-${var.target_environment}-frontend-build"
  retention_in_days = 7

  tags = {
    Name        = "${var.project_name}-${var.target_environment}-frontend-build-logs"
    Environment = var.environment
    TargetEnv   = var.target_environment
    Project     = var.project_name
  }
}

resource "aws_cloudwatch_log_group" "codebuild_backend" {
  name              = "/aws/codebuild/${var.project_name}-${var.target_environment}-backend-build"
  retention_in_days = 7

  tags = {
    Name        = "${var.project_name}-${var.target_environment}-backend-build-logs"
    Environment = var.environment
    TargetEnv   = var.target_environment
    Project     = var.project_name
  }
}

# CodePipeline for Frontend
resource "aws_codepipeline" "frontend" {
  name     = "${var.project_name}-${var.target_environment}-frontend-pipeline"
  role_arn = aws_iam_role.codepipeline_role.arn

  artifact_store {
    location = aws_s3_bucket.pipeline_artifacts.bucket
    type     = "S3"
  }

  stage {
    name = "Source"

    action {
      name             = "Source"
      category         = "Source"
      owner            = "AWS"
      provider         = "CodeStarSourceConnection"
      version          = "1"
      output_artifacts = ["source_output"]

      configuration = {
        ConnectionArn    = var.github_connection_arn
        FullRepositoryId = var.github_repo
        BranchName       = var.github_branch
      }
    }
  }

  stage {
    name = "Approve"

    action {
      name     = "Manual_Approval"
      category = "Approval"
      owner    = "AWS"
      provider = "Manual"
      version  = "1"

      configuration = {
        CustomData = "Please review the frontend changes and approve deployment to ${var.target_environment}"
      }
    }
  }

  stage {
    name = "Build"

    action {
      name             = "Build"
      category         = "Build"
      owner            = "AWS"
      provider         = "CodeBuild"
      input_artifacts  = ["source_output"]
      output_artifacts = ["build_output"]
      version          = "1"

      configuration = {
        ProjectName = aws_codebuild_project.frontend.name
      }
    }
  }

  stage {
    name = "Deploy"

    action {
      name            = "Deploy"
      category        = "Deploy"
      owner           = "AWS"
      provider        = "ECS"
      input_artifacts = ["build_output"]
      version         = "1"

      configuration = {
        ClusterName = var.ecs_cluster_name
        ServiceName = var.frontend_service_name
        FileName    = "imagedefinitions.json"
      }
    }
  }

  tags = {
    Name        = "${var.project_name}-${var.target_environment}-frontend-pipeline"
    Environment = var.environment
    TargetEnv   = var.target_environment
    Project     = var.project_name
  }
}

# CodePipeline for Backend
resource "aws_codepipeline" "backend" {
  name     = "${var.project_name}-${var.target_environment}-backend-pipeline"
  role_arn = aws_iam_role.codepipeline_role.arn

  artifact_store {
    location = aws_s3_bucket.pipeline_artifacts.bucket
    type     = "S3"
  }

  stage {
    name = "Source"

    action {
      name             = "Source"
      category         = "Source"
      owner            = "AWS"
      provider         = "CodeStarSourceConnection"
      version          = "1"
      output_artifacts = ["source_output"]

      configuration = {
        ConnectionArn    = var.github_connection_arn
        FullRepositoryId = var.github_repo
        BranchName       = var.github_branch
      }
    }
  }

  stage {
    name = "Approve"

    action {
      name     = "Manual_Approval"
      category = "Approval"
      owner    = "AWS"
      provider = "Manual"
      version  = "1"

      configuration = {
        CustomData = "Please review the backend API changes and approve deployment to ${var.target_environment}"
      }
    }
  }

  stage {
    name = "Build"

    action {
      name             = "Build"
      category         = "Build"
      owner            = "AWS"
      provider         = "CodeBuild"
      input_artifacts  = ["source_output"]
      output_artifacts = ["build_output"]
      version          = "1"

      configuration = {
        ProjectName = aws_codebuild_project.backend.name
      }
    }
  }

  stage {
    name = "Deploy"

    action {
      name            = "Deploy"
      category        = "Deploy"
      owner           = "AWS"
      provider        = "ECS"
      input_artifacts = ["build_output"]
      version         = "1"

      configuration = {
        ClusterName = var.ecs_cluster_name
        ServiceName = var.backend_service_name
        FileName    = "imagedefinitions.json"
      }
    }
  }

  tags = {
    Name        = "${var.project_name}-${var.target_environment}-backend-pipeline"
    Environment = var.environment
    TargetEnv   = var.target_environment
    Project     = var.project_name
  }
}

