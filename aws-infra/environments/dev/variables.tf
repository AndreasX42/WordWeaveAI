# AWS Configuration
variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-east-1"
}

variable "aws_profile" {
  description = "AWS CLI/profile name used as source credentials"
  type        = string
  default     = "personal"
}

variable "terraform_assume_role_arn" {
  description = "IAM Role ARN for Terraform to assume (recommended). If null, Terraform uses the source credentials directly."
  type        = string
  default     = null
}

variable "terraform_state_bucket" {
  description = "S3 bucket name that stores Terraform state for this repo"
  type        = string
}

variable "terraform_common_state_key" {
  description = "S3 object key for the common environment's Terraform state"
  type        = string
  default     = "common/terraform.tfstate"
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

# Vocab processor Lambda (OpenAI / Instructor)
variable "vocab_llm_node_model" {
  description = "OpenAI model ID for VOCAB_LLM_NODE_MODEL on the vocab-processor Lambda"
  type        = string
  default     = "gpt-4.1-mini-2025-04-14"
}

variable "vocab_llm_supervisor_model" {
  description = "OpenAI model ID for VOCAB_LLM_SUPERVISOR_MODEL on the vocab-processor Lambda"
  type        = string
  default     = "gpt-4.1-2025-04-14"
}

# ECS backend: SSM paths for secrets/config (env key -> parameter path)
variable "backend_ssm_parameter_paths" {
  description = "Map of backend container env var name to SSM Parameter Store path"
  type        = map(string)
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

variable "apex_domain_name" {
  description = "Optional apex domain Alias A to the ALB (e.g. wordweave.xyz). Omit or set null to skip."
  type        = string
  default     = null
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

# WAF Configuration
variable "waf_rate_limit_requests_per_5_minutes" {
  description = "Maximum number of requests per IP address per 5 minutes for WAF rate limiting"
  type        = number
  default     = 1000
}

variable "waf_blocked_ip_addresses" {
  description = "List of IP addresses to block via WAF"
  type        = list(string)
  default     = []
}

variable "waf_log_retention_days" {
  description = "Number of days to retain WAF logs"
  type        = number
  default     = 30
}

variable "waf_enable_logging" {
  description = "Enable WAF logging to CloudWatch (increases costs but provides monitoring)"
  type        = bool
  default     = true
}

variable "waf_rate_limit_response_message" {
  description = "Custom message to display when WAF rate limit is exceeded"
  type        = string
  default     = "Rate limit exceeded. Please try again in 5 minutes."
}
