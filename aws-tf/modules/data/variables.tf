variable "project_name" {
  description = "Name of the project"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "s3_media_bucket_name" {
  description = "Name of the S3 bucket for media storage"
  type        = string
}

variable "dynamodb_user_table_name" {
  description = "Name of the DynamoDB user table"
  type        = string
}

variable "dynamodb_connections_table_name" {
  description = "Name of the DynamoDB connections table"
  type        = string
}

variable "dynamodb_vocab_table_name" {
  description = "Name of the DynamoDB vocab table"
  type        = string
}

variable "dynamodb_vocab_media_table_name" {
  description = "Name of the DynamoDB vocab media table"
  type        = string
}

variable "dynamodb_vocab_list_table_name" {
  description = "Name of the DynamoDB vocab list table"
  type        = string
} 