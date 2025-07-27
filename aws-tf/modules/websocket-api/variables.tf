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

variable "websocket_handler_zip_path" {
  description = "Path to the WebSocket handler ZIP file"
  type        = string
}

variable "lambda_layer_arn" {
  description = "ARN of the Lambda layer"
  type        = string
  default     = null
}

variable "dynamodb_connections_table_name" {
  description = "Name of the connections DynamoDB table"
  type        = string
}

variable "dynamodb_connections_table_arn" {
  description = "ARN of the connections DynamoDB table"
  type        = string
} 