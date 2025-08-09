variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Name of the project"
  type        = string
  default     = "wordweave"
}

variable "ecr_frontend_repo_name" {
  description = "Name of the ECR repository for frontend"
  type        = string
}

variable "ecr_backend_repo_name" {
  description = "Name of the ECR repository for backend"
  type        = string
}

variable "domain_name" {
  description = "Top level domain name"
  type        = string
}

