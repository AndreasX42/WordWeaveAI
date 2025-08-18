# AWS WAF Web ACL for IP-based rate limiting
resource "aws_wafv2_web_acl" "main" {
  name        = "${var.project_name}-waf-web-acl"
  description = "Optimized WAF Web ACL with IP-based rate limiting for ${var.project_name}"
  scope       = "REGIONAL"

  default_action {
    allow {}
  }

  # Custom response body for rate limiting
  custom_response_body {
    key          = "rate_limited_json"
    content_type = "APPLICATION_JSON"
    content      = jsonencode({
      error   = "rate_limited"
      message = var.rate_limit_response_message
      code    = "RATE_LIMIT_EXCEEDED"
    })
  }

  # Custom response body for blocked IPs
  custom_response_body {
    key          = "blocked_ip_json"
    content_type = "APPLICATION_JSON"
    content      = jsonencode({
      error   = "access_denied"
      message = "Access denied from this IP address."
      code    = "IP_BLOCKED"
    })
  }

  # More granular rate limiting rule with custom response
  rule {
    name     = "StrictRateLimit"
    priority = 1

    statement {
      rate_based_statement {
        limit              = var.rate_limit_requests_per_5_minutes
        aggregate_key_type = "IP"
      }
    }

    action {
      block {
        custom_response {
          response_code            = 418
          custom_response_body_key = "rate_limited_json"
          response_header {
            name  = "Retry-After"
            value = "300"
          }
        }
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "StrictRateLimit"
      sampled_requests_enabled   = true
    }
  }

  # Block known malicious IPs
  rule {
    name     = "BlockedIPs"
    priority = 2

    statement {
      ip_set_reference_statement {
        arn = aws_wafv2_ip_set.blocked_ips.arn
      }
    }

    action {
      block {
        custom_response {
          response_code            = 418
          custom_response_body_key = "blocked_ip_json"
        }
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "BlockedIPs"
      sampled_requests_enabled   = true
    }
  }

  # Combined security rules
  rule {
    name     = "SecurityRules"
    priority = 3

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesCommonRuleSet"
        vendor_name = "AWS"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "SecurityRules"
      sampled_requests_enabled   = true
    }
  }

  visibility_config {
    cloudwatch_metrics_enabled = true
    metric_name                = "WebACL"
    sampled_requests_enabled   = true
  }

  tags = {
    Name        = "${var.project_name}-waf-web-acl"
    Environment = var.environment
    Project     = var.project_name
  }
}





# IP Set for blocked IPs
resource "aws_wafv2_ip_set" "blocked_ips" {
  name               = "${var.project_name}-blocked-ips"
  description        = "IP addresses to block"
  scope              = "REGIONAL"
  ip_address_version = "IPV4"
  addresses          = var.blocked_ip_addresses

  tags = {
    Name        = "${var.project_name}-blocked-ips"
    Environment = var.environment
    Project     = var.project_name
  }
}

# Associate WAF with ALB
resource "aws_wafv2_web_acl_association" "alb" {
  resource_arn = var.alb_arn
  web_acl_arn  = aws_wafv2_web_acl.main.arn
}

# CloudWatch Log Group for WAF logs
resource "aws_cloudwatch_log_group" "waf_logs" {
  name              = "/aws/waf/${var.project_name}-web-acl"
  retention_in_days = var.log_retention_days

  tags = {
    Name        = "${var.project_name}-waf-logs"
    Environment = var.environment
    Project     = var.project_name
  }
}

# Optional WAF Logging Configuration
resource "aws_wafv2_web_acl_logging_configuration" "main" {
  count = var.enable_waf_logging ? 1 : 0
  
  log_destination_configs = [aws_cloudwatch_log_group.waf_logs.arn]
  resource_arn            = aws_wafv2_web_acl.main.arn
}
