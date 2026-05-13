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

