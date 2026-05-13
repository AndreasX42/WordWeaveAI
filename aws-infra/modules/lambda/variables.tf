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

variable "aws_account_id" {
  description = "AWS account ID"
  type        = string
}

variable "lambda_layer_zip_path" {
  description = "Path to the Lambda layer ZIP file"
  type        = string
}

variable "lambda_layer_arn" {
  description = "ARN of the shared Lambda layer"
  type        = string
}

variable "lambda_function_zip_path" {
  description = "Path to the Lambda function ZIP file"
  type        = string
}

variable "sqs_queue_arn" {
  description = "ARN of the SQS queue"
  type        = string
}

# DynamoDB Configuration
variable "dynamodb_user_table_name" {
  description = "Name of the user DynamoDB table"
  type        = string
}

variable "dynamodb_user_table_arn" {
  description = "ARN of the user DynamoDB table"
  type        = string
}

variable "dynamodb_vocab_table_name" {
  description = "Name of the vocab DynamoDB table"
  type        = string
}

variable "dynamodb_vocab_table_arn" {
  description = "ARN of the vocab DynamoDB table"
  type        = string
}

variable "dynamodb_vocab_media_table_name" {
  description = "Name of the vocab media DynamoDB table"
  type        = string
}

variable "dynamodb_vocab_media_table_arn" {
  description = "ARN of the vocab media DynamoDB table"
  type        = string
}

variable "dynamodb_connections_table_name" {
  description = "Name of the connections DynamoDB table"
  type        = string
}

variable "dynamodb_connections_table_arn" {
  description = "ARN of the connections DynamoDB table"
  type        = string
}

# S3 Configuration
variable "s3_bucket_name" {
  description = "Name of the S3 bucket"
  type        = string
}

variable "s3_bucket_arn" {
  description = "ARN of the S3 bucket"
  type        = string
}

# WebSocket API Configuration
variable "enable_websocket_iam_policy" {
  description = "Attach execute-api ManageConnections permissions. Set true when websocket_api_id is provided (must be literal true/false—not derived from websocket_api_id—so Terraform can plan count)."
  type        = bool
  default     = false
}

variable "websocket_api_id" {
  description = "ID of the WebSocket API"
  type        = string
  default     = null
}

variable "websocket_api_endpoint" {
  description = "Endpoint of the WebSocket API"
  type        = string
  default     = null
}

variable "vocab_llm_node_model" {
  description = "OpenAI model ID for VOCAB_LLM_NODE_MODEL (Instructor node_executor)."
  type        = string
  default     = "gpt-4.1-mini-2025-04-14"
}

variable "vocab_llm_supervisor_model" {
  description = "OpenAI model ID for VOCAB_LLM_SUPERVISOR_MODEL (supervisor router)."
  type        = string
  default     = "gpt-4.1-2025-04-14"
}
