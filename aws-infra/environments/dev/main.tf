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
  region  = var.aws_region
  profile = "personal"
}

# Data sources
data "aws_caller_identity" "current" {}
data "aws_availability_zones" "available" {
  state = "available"
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

  project_name              = var.project_name
  environment               = var.environment
  aws_region                = var.aws_region
  enable_container_insights = var.enable_container_insights
  log_retention_days        = var.log_retention_days
  dynamodb_table_arns       = [module.data.dynamodb_user_table_arn, module.data.dynamodb_vocab_table_arn, module.data.dynamodb_vocab_media_table_arn, module.data.dynamodb_connections_table_arn, module.data.dynamodb_vocab_list_table_arn]
  s3_bucket_arn             = module.data.s3_vocab_bucket_arn
  sqs_queue_arn             = module.sqs.queue_arn
  frontend_cpu              = var.frontend_cpu
  frontend_memory           = var.frontend_memory
  frontend_image_uri        = "${data.terraform_remote_state.common.outputs.ecr_frontend_repository_url}:latest"
  backend_cpu               = var.backend_cpu
  backend_memory            = var.backend_memory
  backend_image_uri         = "${data.terraform_remote_state.common.outputs.ecr_backend_repository_url}:latest"
  # Provide envs as a map (module will derive the list)
  backend_env_map = {
    SQS_VOCAB_REQUEST_QUEUE_URL     = module.sqs.queue_url
    DYNAMODB_USER_TABLE_NAME        = var.dynamodb_user_table_name
    DYNAMODB_VOCAB_TABLE_NAME       = var.dynamodb_vocab_table_name
    DYNAMODB_VOCAB_MEDIA_TABLE_NAME = var.dynamodb_vocab_media_table_name
    DYNAMODB_VOCAB_LIST_TABLE_NAME  = var.dynamodb_vocab_list_table_name
    DYNAMODB_CONNECTIONS_TABLE_NAME = var.dynamodb_connections_table_name
    S3_MEDIA_BUCKET_NAME            = var.s3_media_bucket_name
    SENTRY_ENVIRONMENT              = "${var.project_name}-${var.environment}"
  }
  # Provide SSM parameter paths (module will fetch, build secrets, and IAM scope)
  backend_ssm_parameter_paths = {
    GOOGLE_CLIENT_ID             = "/wordweave/${var.environment}/backend/google-client-id"
    GOOGLE_CLIENT_SECRET         = "/wordweave/${var.environment}/backend/google-client-secret"
    GOOGLE_REDIRECT_URL          = "/wordweave/${var.environment}/backend/google-redirect-url"
    SENTRY_DSN                   = "/apikeys/SENTRY_DSN"
    JWT_SECRET_KEY               = "/wordweave/${var.environment}/backend/jwt-secret-key"
    JWT_EXPIRATION_TIME          = "/wordweave/${var.environment}/backend/jwt-expiration-time"
    CORS_ALLOWED_ORIGINS         = "/wordweave/${var.environment}/backend/cors-allowed-origins"
    FRONTEND_URL                 = "/wordweave/${var.environment}/backend/frontend-url"
    MAX_VOCAB_REQUESTS_FREE_TIER = "/wordweave/${var.environment}/backend/max-vocab-requests-free-tier"
    SES_FROM_EMAIL               = "/wordweave/${var.environment}/backend/ses-from-email"
    SES_FROM_NAME                = "/wordweave/${var.environment}/backend/ses-from-name"
  }
  desired_count               = var.desired_count
  ecs_tasks_security_group_id = module.alb.ecs_tasks_security_group_id
  public_subnet_ids           = module.vpc.public_subnet_ids
  frontend_target_group_arn   = module.alb.frontend_target_group_arn
  backend_target_group_arn    = module.alb.backend_target_group_arn
  alb_listener_arn            = module.alb.https_listener_arn

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
  ecs_cluster_name                     = module.ecs.cluster_name
  frontend_service_name                = module.ecs.frontend_service_name
  backend_service_name                 = module.ecs.backend_service_name
  ecs_frontend_task_role_arn           = module.ecs.ecs_frontend_task_role_arn
  ecs_backend_task_role_arn            = module.ecs.ecs_backend_task_role_arn
  ecs_frontend_task_execution_role_arn = module.ecs.ecs_frontend_task_execution_role_arn
  ecs_backend_task_execution_role_arn  = module.ecs.ecs_backend_task_execution_role_arn

  # Frontend Configuration (URLs for build-time injection)
  backend_domain_name    = var.backend_domain_name
  websocket_api_endpoint = module.websocket_api.websocket_api_endpoint
} 