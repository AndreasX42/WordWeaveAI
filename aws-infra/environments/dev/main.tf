terraform {
  required_version = ">= 1.2"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
  profile = "personal"
}

# Data sources
data "aws_caller_identity" "current" {}
data "aws_availability_zones" "available" {
  state = "available"
}

data "aws_ssm_parameter" "sentry_dsn" {
  name = "/apikeys/SENTRY_DSN"
  with_decryption = true
}

## Google OAuth SSM parameters
data "aws_ssm_parameter" "google_client_id" {
  name            = "/wordweave/${var.environment}/backend/google-client-id"
  with_decryption = true
}

data "aws_ssm_parameter" "google_client_secret" {
  name            = "/wordweave/${var.environment}/backend/google-client-secret"
  with_decryption = true
}

data "aws_ssm_parameter" "google_redirect_url" {
  name            = "/wordweave/${var.environment}/backend/google-redirect-url"
  with_decryption = true
}

data "aws_ssm_parameter" "jwt_secret_key" {
  name            = "/wordweave/${var.environment}/backend/jwt-secret-key"
  with_decryption = true
}

data "aws_ssm_parameter" "jwt_expiration_time" {
  name            = "/wordweave/${var.environment}/backend/jwt-expiration-time"
  with_decryption = true
}

data "aws_ssm_parameter" "cors_allowed_origins" {
  name            = "/wordweave/${var.environment}/backend/cors-allowed-origins"
  with_decryption = true
}

data "aws_ssm_parameter" "frontend_url" {
  name            = "/wordweave/${var.environment}/backend/frontend-url"
  with_decryption = true
}

data "aws_ssm_parameter" "max_vocab_requests_free_tier" {
  name            = "/wordweave/${var.environment}/backend/max-vocab-requests-free-tier"
  with_decryption = true
}

data "aws_ssm_parameter" "ses_from_email" {
  name            = "/wordweave/${var.environment}/backend/ses-from-email"
  with_decryption = true
}

data "aws_ssm_parameter" "ses_from_name" {
  name            = "/wordweave/${var.environment}/backend/ses-from-name"
  with_decryption = true
}

# Remote state for common environment
data "terraform_remote_state" "common" {
  backend = "local" # Change to "s3" if using S3 backend
  config = {
    path = "../common/terraform.tfstate"
  }
}

# Local values
locals {
  aws_account_id = data.aws_caller_identity.current.account_id
  common_tags = {
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "terraform"
  }

  backend_secrets = [
    {
      name      = "GOOGLE_CLIENT_ID"
      valueFrom = data.aws_ssm_parameter.google_client_id.arn
    },
    {
      name      = "GOOGLE_CLIENT_SECRET"
      valueFrom = data.aws_ssm_parameter.google_client_secret.arn
    },
    {
      name      = "GOOGLE_REDIRECT_URL"
      valueFrom = data.aws_ssm_parameter.google_redirect_url.arn
    },
    {
      name      = "SENTRY_DSN"
      valueFrom = data.aws_ssm_parameter.sentry_dsn.arn
    },
    {
      name      = "JWT_SECRET_KEY"
      valueFrom = data.aws_ssm_parameter.jwt_secret_key.arn
    },
    {
      name      = "JWT_EXPIRATION_TIME"
      valueFrom = data.aws_ssm_parameter.jwt_expiration_time.arn
    },
    {
      name      = "CORS_ALLOWED_ORIGINS"
      valueFrom = data.aws_ssm_parameter.cors_allowed_origins.arn
    },
    {
      name      = "FRONTEND_URL"
      valueFrom = data.aws_ssm_parameter.frontend_url.arn
    },
    {
      name      = "MAX_VOCAB_REQUESTS_FREE_TIER"
      valueFrom = data.aws_ssm_parameter.max_vocab_requests_free_tier.arn
    },
    {
      name      = "SES_FROM_EMAIL"
      valueFrom = data.aws_ssm_parameter.ses_from_email.arn
    },
    {
      name      = "SES_FROM_NAME"
      valueFrom = data.aws_ssm_parameter.ses_from_name.arn
    },
  ]

  backend_environment_variables = [
    # Infrastructure-dependent values (generated dynamically)
    {
      name  = "SQS_VOCAB_REQUEST_QUEUE_URL"
      value = module.sqs.queue_url
    },
    {
      name  = "DYNAMODB_USER_TABLE_NAME"
      value = var.dynamodb_user_table_name
    },
    {
      name  = "DYNAMODB_VOCAB_TABLE_NAME"
      value = var.dynamodb_vocab_table_name
    },
    {
      name  = "DYNAMODB_VOCAB_MEDIA_TABLE_NAME"
      value = var.dynamodb_vocab_media_table_name
    },
    {
      name  = "DYNAMODB_VOCAB_LIST_TABLE_NAME"
      value = var.dynamodb_vocab_list_table_name
    },
    {
      name  = "DYNAMODB_CONNECTIONS_TABLE_NAME"
      value = var.dynamodb_connections_table_name
    },
    {
      name  = "S3_MEDIA_BUCKET_NAME"
      value = var.s3_media_bucket_name
    },
    {
      name  = "SENTRY_ENVIRONMENT"
      value = "${var.project_name}-${var.environment}"
    },
  ]
}

# VPC Module
module "vpc" {
  source = "../../modules/vpc"

  project_name       = var.project_name
  environment        = var.environment
  vpc_cidr           = var.vpc_cidr
  availability_zones = slice(data.aws_availability_zones.available.names, 0, 2)
  enable_flow_logs   = var.enable_vpc_flow_logs
}

# Data Stack Module
module "data" {
  source = "../../modules/data"

  project_name                    = var.project_name
  environment                     = var.environment
  s3_media_bucket_name            = var.s3_media_bucket_name
  dynamodb_user_table_name        = var.dynamodb_user_table_name
  dynamodb_connections_table_name = var.dynamodb_connections_table_name
  dynamodb_vocab_table_name       = var.dynamodb_vocab_table_name
  dynamodb_vocab_media_table_name = var.dynamodb_vocab_media_table_name
  dynamodb_vocab_list_table_name  = var.dynamodb_vocab_list_table_name
}

module "alb" {
  source = "../../modules/alb"

  project_name         = var.project_name
  environment          = var.environment
  vpc_id               = module.vpc.vpc_id
  public_subnet_ids    = module.vpc.public_subnet_ids
  acm_certificate_arn  = try(data.terraform_remote_state.common.outputs.acm_certificate_arn, var.acm_certificate_arn)
  frontend_domain_name = var.frontend_domain_name
  backend_domain_name  = var.backend_domain_name
  route53_zone_id      = try(data.terraform_remote_state.common.outputs.route53_zone_id, null)
}

# SQS Module
module "sqs" {
  source = "../../modules/sqs"

  project_name = var.project_name
  environment  = var.environment
}

# Lambda Layer Module
module "lambda_layer" {
  source = "../../modules/lambda-layer"

  project_name          = var.project_name
  environment           = var.environment
  lambda_layer_zip_path = var.lambda_layer_zip_path
}

# WebSocket API Module
module "websocket_api" {
  source = "../../modules/websocket-api"

  project_name                    = var.project_name
  environment                     = var.environment
  aws_region                      = var.aws_region
  aws_account_id                  = local.aws_account_id
  websocket_handler_zip_path      = var.websocket_handler_zip_path
  lambda_layer_arn                = module.lambda_layer.lambda_layer_arn
  dynamodb_connections_table_name = module.data.dynamodb_connections_table_name
  dynamodb_connections_table_arn  = module.data.dynamodb_connections_table_arn
}

# Lambda Module
module "lambda" {
  source = "../../modules/lambda"

  project_name                    = var.project_name
  environment                     = var.environment
  aws_region                      = var.aws_region
  aws_account_id                  = local.aws_account_id
  lambda_layer_zip_path           = var.lambda_layer_zip_path
  lambda_layer_arn                = module.lambda_layer.lambda_layer_arn
  lambda_function_zip_path        = var.lambda_function_zip_path
  sqs_queue_arn                   = module.sqs.queue_arn
  dynamodb_user_table_name        = module.data.dynamodb_user_table_name
  dynamodb_user_table_arn         = module.data.dynamodb_user_table_arn
  dynamodb_vocab_table_name       = module.data.dynamodb_vocab_table_name
  dynamodb_vocab_table_arn        = module.data.dynamodb_vocab_table_arn
  dynamodb_vocab_media_table_name = module.data.dynamodb_vocab_media_table_name
  dynamodb_vocab_media_table_arn  = module.data.dynamodb_vocab_media_table_arn
  dynamodb_connections_table_name = module.data.dynamodb_connections_table_name
  dynamodb_connections_table_arn  = module.data.dynamodb_connections_table_arn
  s3_bucket_name                  = module.data.s3_vocab_bucket_id
  s3_bucket_arn                   = module.data.s3_vocab_bucket_arn
  websocket_api_id                = module.websocket_api.websocket_api_id
  websocket_api_endpoint          = module.websocket_api.websocket_api_endpoint

  depends_on = [module.sqs, module.data]
}

module "ecs" {
  source = "../../modules/ecs"

  project_name                  = var.project_name
  environment                   = var.environment
  aws_region                    = var.aws_region
  enable_container_insights     = var.enable_container_insights
  log_retention_days            = var.log_retention_days
  dynamodb_table_arns           = [module.data.dynamodb_user_table_arn, module.data.dynamodb_vocab_table_arn, module.data.dynamodb_vocab_media_table_arn, module.data.dynamodb_connections_table_arn, module.data.dynamodb_vocab_list_table_arn]
  s3_bucket_arn                 = module.data.s3_vocab_bucket_arn
  sqs_queue_arn                 = module.sqs.queue_arn
  frontend_cpu                  = var.frontend_cpu
  frontend_memory               = var.frontend_memory
  frontend_image_uri            = "${data.terraform_remote_state.common.outputs.ecr_frontend_repository_url}:latest"
  backend_cpu                   = var.backend_cpu
  backend_memory                = var.backend_memory
  backend_image_uri             = "${data.terraform_remote_state.common.outputs.ecr_backend_repository_url}:latest"
  backend_environment_variables = local.backend_environment_variables
  backend_secrets               = local.backend_secrets
  desired_count                 = var.desired_count
  ecs_tasks_security_group_id   = module.alb.ecs_tasks_security_group_id
  public_subnet_ids             = module.vpc.public_subnet_ids
  frontend_target_group_arn     = module.alb.frontend_target_group_arn
  backend_target_group_arn      = module.alb.backend_target_group_arn
  alb_listener_arn              = module.alb.https_listener_arn

  # Ensure infrastructure is created before environment variables are used
  depends_on = [module.data, module.sqs]
}

# CI/CD Pipeline Module
module "cicd_pipeline" {
  source = "../../modules/cicd-pipeline"

  project_name       = var.project_name
  environment        = var.environment
  target_environment = var.environment
  aws_region         = var.aws_region
  aws_account_id     = local.aws_account_id

  # GitHub Configuration
  github_connection_arn = var.github_connection_arn
  github_repo           = var.github_repo
  github_branch         = var.github_branch

  # ECR Repository names from common environment
  frontend_ecr_repo_name = data.terraform_remote_state.common.outputs.ecr_frontend_repository_name
  backend_ecr_repo_name  = data.terraform_remote_state.common.outputs.ecr_backend_repository_name

  # ECS Configuration (deployment targets)
  ecs_cluster_name            = module.ecs.cluster_name
  frontend_service_name       = module.ecs.frontend_service_name
  backend_service_name        = module.ecs.backend_service_name
  ecs_task_execution_role_arn = module.ecs.ecs_task_execution_role_arn
  ecs_task_role_arn           = module.ecs.ecs_task_role_arn

  # Frontend Configuration (URLs for build-time injection)
  backend_domain_name    = var.backend_domain_name
  websocket_api_endpoint = module.websocket_api.websocket_api_endpoint
} 