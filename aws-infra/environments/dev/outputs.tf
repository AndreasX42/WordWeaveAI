# VPC Outputs
output "vpc_id" {
  description = "ID of the VPC"
  value       = module.vpc.vpc_id
}

output "public_subnet_ids" {
  description = "List of public subnet IDs"
  value       = module.vpc.public_subnet_ids
}

# Load Balancer Outputs
output "alb_dns_name" {
  description = "DNS name of the ALB"
  value       = module.alb.alb_dns_name
}

output "alb_zone_id" {
  description = "Zone ID of the ALB"
  value       = module.alb.alb_zone_id
}

# ECS Outputs
output "ecs_cluster_name" {
  description = "Name of the ECS cluster"
  value       = module.ecs.cluster_name
}

output "frontend_service_name" {
  description = "Name of the frontend ECS service"
  value       = module.ecs.frontend_service_name
}

output "backend_service_name" {
  description = "Name of the backend ECS service"
  value       = module.ecs.backend_service_name
}

output "frontend_ecr_repo_name" {
  description = "Name of the frontend ECR repository"
  value       = data.terraform_remote_state.common.outputs.ecr_frontend_repository_name
}

output "backend_ecr_repo_name" {
  description = "Name of the backend ECR repository"
  value       = data.terraform_remote_state.common.outputs.ecr_backend_repository_name
}

# Lambda Outputs
output "lambda_function_name" {
  description = "Name of the vocab processor Lambda function"
  value       = module.lambda.lambda_function_name
}

output "lambda_function_arn" {
  description = "ARN of the vocab processor Lambda function"
  value       = module.lambda.lambda_function_arn
}

# WebSocket API Outputs
output "websocket_api_endpoint" {
  description = "WebSocket API endpoint URL"
  value       = module.websocket_api.websocket_api_endpoint
}

# SQS Outputs
output "sqs_queue_url" {
  description = "URL of the SQS queue"
  value       = module.sqs.queue_url
}

# DynamoDB Outputs
output "dynamodb_table_names" {
  description = "Names of the DynamoDB tables"
  value = {
    user_table        = module.data.dynamodb_user_table_name
    vocab_table       = module.data.dynamodb_vocab_table_name
    connections_table = module.data.dynamodb_connections_table_name
    vocab_media_table = module.data.dynamodb_vocab_media_table_name
    vocab_list_table  = module.data.dynamodb_vocab_list_table_name
  }
}

# S3 Outputs
output "s3_bucket_name" {
  description = "Name of the S3 bucket"
  value       = module.data.s3_vocab_bucket_id
}

# Domain Outputs
output "frontend_domain" {
  description = "Frontend domain name"
  value       = var.frontend_domain_name
}

output "backend_domain" {
  description = "Backend domain name"
  value       = var.backend_domain_name
}

# Security Group Outputs
output "alb_security_group_id" {
  description = "ID of the ALB security group"
  value       = module.alb.alb_security_group_id
}

output "ecs_tasks_security_group_id" {
  description = "ID of the ECS tasks security group"
  value       = module.alb.ecs_tasks_security_group_id
}

# CI/CD Pipeline Outputs
output "pipeline_artifacts_bucket_name" {
  description = "Name of the pipeline artifacts S3 bucket"
  value       = module.cicd_pipeline.pipeline_artifacts_bucket_name
}

output "frontend_pipeline_name" {
  description = "Name of the frontend CodePipeline"
  value       = module.cicd_pipeline.frontend_pipeline_name
}

output "backend_pipeline_name" {
  description = "Name of the backend CodePipeline"
  value       = module.cicd_pipeline.backend_pipeline_name
}

output "frontend_codebuild_project_name" {
  description = "Name of the frontend CodeBuild project"
  value       = module.cicd_pipeline.frontend_codebuild_project_name
}

output "backend_codebuild_project_name" {
  description = "Name of the backend CodeBuild project"
  value       = module.cicd_pipeline.backend_codebuild_project_name
}

output "codepipeline_role_arn" {
  description = "ARN of the CodePipeline service role"
  value       = module.cicd_pipeline.codepipeline_role_arn
}

output "codebuild_role_arn" {
  description = "ARN of the CodeBuild service role"
  value       = module.cicd_pipeline.codebuild_role_arn
} 