variable "project_name" {
  description = "Name of the project"
  type        = string
}

variable "environment" {
  description = "Environment name (common, dev, prod, etc.)"
  type        = string
}

variable "target_environment" {
  description = "Target environment for deployment (dev, prod, etc.)"
  type        = string
  default     = "dev"
}

variable "aws_region" {
  description = "AWS region"
  type        = string
}

variable "aws_account_id" {
  description = "AWS account ID"
  type        = string
}

variable "github_connection_arn" {
  description = "ARN of the GitHub connection"
  type        = string
}

variable "github_repo" {
  description = "GitHub repository (owner/repo)"
  type        = string
}

variable "github_branch" {
  description = "GitHub branch to build from"
  type        = string
  default     = "main"
}

variable "frontend_ecr_repo_name" {
  description = "Name of the frontend ECR repository"
  type        = string
}

variable "backend_ecr_repo_name" {
  description = "Name of the backend ECR repository"
  type        = string
}

variable "ecs_cluster_name" {
  description = "Name of the ECS cluster for deployment target"
  type        = string
}

variable "frontend_service_name" {
  description = "Name of the frontend ECS service for deployment target"
  type        = string
}

variable "backend_service_name" {
  description = "Name of the backend ECS service for deployment target"
  type        = string
}


variable "ecs_frontend_task_execution_role_arn" {
  description = "ARN of the ECS frontend task execution role for deployment target"
  type        = string
}

variable "ecs_backend_task_execution_role_arn" {
  description = "ARN of the ECS backend task execution role for deployment target"
  type        = string
}


variable "ecs_frontend_task_role_arn" {
  description = "ARN of the ECS frontend task role for deployment target"
  type        = string
}

variable "ecs_backend_task_role_arn" {
  description = "ARN of the ECS backend task role for deployment target"
  type        = string
}

variable "backend_domain_name" {
  description = "Domain name for the backend API (used for frontend BASE_URL)"
  type        = string
}

variable "websocket_api_endpoint" {
  description = "WebSocket API endpoint URL"
  type        = string
} 