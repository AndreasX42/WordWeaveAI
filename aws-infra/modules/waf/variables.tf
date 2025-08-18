variable "project_name" {
  description = "Name of the project"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "alb_arn" {
  description = "ARN of the Application Load Balancer to associate with WAF"
  type        = string
}

variable "rate_limit_requests_per_5_minutes" {
  description = "Maximum number of requests per IP address per 5 minutes"
  type        = number
  default     = 2000
}

variable "blocked_ip_addresses" {
  description = "List of IP addresses to block"
  type        = list(string)
  default     = []
}

variable "log_retention_days" {
  description = "Number of days to retain WAF logs in CloudWatch"
  type        = number
  default     = 30
}

variable "enable_waf_logging" {
  description = "Enable WAF logging to CloudWatch (increases costs but provides monitoring)"
  type        = bool
  default     = true
}

variable "rate_limit_response_message" {
  description = "Custom message to display when rate limit is exceeded"
  type        = string
  default     = "Too many requests. Please try again later."
}
