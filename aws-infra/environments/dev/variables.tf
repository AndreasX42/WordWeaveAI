# AWS Configuration
variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "dev"
}

variable "project_name" {
  description = "Name of the project"
  type        = string
  default     = "wordweave"
}

# VPC Configuration
variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "enable_vpc_flow_logs" {
  description = "Enable VPC flow logs"
  type        = bool
  default     = false
}

# S3 Configuration
variable "s3_media_bucket_name" {
  description = "Name of the S3 bucket for media storage"
  type        = string
}

# DynamoDB Configuration
variable "dynamodb_user_table_name" {
  description = "Name of the DynamoDB user table"
  type        = string
  default     = "wordweave-dev-users"
}

variable "dynamodb_connections_table_name" {
  description = "Name of the DynamoDB connections table"
  type        = string
  default     = "wordweave-dev-connections"
}

variable "dynamodb_vocab_table_name" {
  description = "Name of the DynamoDB vocab table"
  type        = string
  default     = "wordweave-dev-vocab"
}

variable "dynamodb_vocab_media_table_name" {
  description = "Name of the DynamoDB vocab media table"
  type        = string
  default     = "wordweave-dev-vocab-media"
}

variable "dynamodb_vocab_list_table_name" {
  description = "Name of the DynamoDB vocab list table"
  type        = string
  default     = "wordweave-dev-vocab-list"
}

# Lambda Configuration
variable "lambda_layer_zip_path" {
  description = "Path to the Lambda layer ZIP file"
  type        = string
}

variable "lambda_function_zip_path" {
  description = "Path to the Lambda function ZIP file"
  type        = string
}

variable "websocket_handler_zip_path" {
  description = "Path to the WebSocket handler ZIP file"
  type        = string
}

# Domain Configuration
variable "frontend_domain_name" {
  description = "Frontend domain name"
  type        = string
}

variable "backend_domain_name" {
  description = "Backend domain name"
  type        = string
}

variable "acm_certificate_arn" {
  description = "ACM certificate ARN (optional if using common environment)"
  type        = string
  default     = null
}

variable "frontend_cpu" {
  description = "CPU units for frontend task"
  type        = number
  default     = 256
}

variable "frontend_memory" {
  description = "Memory for frontend task"
  type        = number
  default     = 512
}

variable "backend_cpu" {
  description = "CPU units for backend task"
  type        = number
  default     = 512
}

variable "backend_memory" {
  description = "Memory for backend task"
  type        = number
  default     = 1024
}

variable "desired_count" {
  description = "Desired number of tasks"
  type        = number
  default     = 2
}

variable "enable_container_insights" {
  description = "Enable container insights"
  type        = bool
  default     = false
}

variable "log_retention_days" {
  description = "Log retention in days"
  type        = number
  default     = 7
}

variable "backend_environment_variables" {
  description = "A list of environment variables for the backend container."
  type        = any
  default     = []
}

variable "backend_secrets" {
  description = "A list of secrets for the backend container."
  type        = any
  default     = []
}

# Lambda VPC Configuration
variable "enable_lambda_vpc" {
  description = "Enable VPC for Lambda functions"
  type        = bool
  default     = false
}

# CI/CD Configuration
variable "github_connection_arn" {
  description = "ARN of the GitHub connection for CodePipeline"
  type        = string
}

variable "github_repo" {
  description = "GitHub repository (owner/repo) for CodePipeline"
  type        = string
}

variable "github_branch" {
  description = "GitHub branch to build from"
  type        = string
  default     = "master"
} 