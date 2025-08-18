output "web_acl_arn" {
  description = "ARN of the WAF Web ACL"
  value       = aws_wafv2_web_acl.main.arn
}

output "web_acl_id" {
  description = "ID of the WAF Web ACL"
  value       = aws_wafv2_web_acl.main.id
}

output "web_acl_name" {
  description = "Name of the WAF Web ACL"
  value       = aws_wafv2_web_acl.main.name
}

output "blocked_ips_ip_set_arn" {
  description = "ARN of the IP set containing blocked IP addresses"
  value       = aws_wafv2_ip_set.blocked_ips.arn
}

output "blocked_ips_ip_set_id" {
  description = "ID of the IP set containing blocked IP addresses"
  value       = aws_wafv2_ip_set.blocked_ips.id
}



output "cloudwatch_log_group_name" {
  description = "Name of the CloudWatch log group for WAF logs"
  value       = aws_cloudwatch_log_group.waf_logs.name
}
