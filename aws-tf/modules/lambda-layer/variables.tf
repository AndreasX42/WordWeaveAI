variable "project_name" {
  description = "Name of the project"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "lambda_layer_zip_path" {
  description = "Path to the Lambda layer ZIP file"
  type        = string
} 