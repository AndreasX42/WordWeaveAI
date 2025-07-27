variable "project_name" {
  description = "Name of the project"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "aws_region" {
  description = "AWS region"
  type        = string
}

variable "enable_container_insights" {
  description = "Enable CloudWatch Container Insights"
  type        = bool
  default     = false
}

variable "log_retention_days" {
  description = "CloudWatch logs retention in days"
  type        = number
  default     = 7
}

# ECS Task Configuration
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

# Container Images
variable "frontend_image_uri" {
  description = "URI of the frontend container image"
  type        = string
}

variable "backend_image_uri" {
  description = "URI of the backend container image"
  type        = string
}

# Network Configuration
variable "public_subnet_ids" {
  description = "List of public subnet IDs for ECS services"
  type        = list(string)
}

variable "ecs_tasks_security_group_id" {
  description = "Security group ID for ECS tasks"
  type        = string
}

# ALB Configuration
variable "frontend_target_group_arn" {
  description = "ARN of the frontend target group"
  type        = string
}

variable "backend_target_group_arn" {
  description = "ARN of the backend target group"
  type        = string
}

variable "alb_listener_arn" {
  description = "ARN of the ALB HTTPS listener"
  type        = string
}

# IAM Permissions
variable "dynamodb_table_arns" {
  description = "List of DynamoDB table ARNs for backend access"
  type        = list(string)
}

variable "s3_bucket_arn" {
  description = "ARN of the S3 bucket for backend access"
  type        = string
}

variable "sqs_queue_arn" {
  description = "ARN of the SQS queue for backend access"
  type        = string
}

# Backend Environment Variables
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