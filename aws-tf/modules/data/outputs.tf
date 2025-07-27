output "s3_vocab_bucket_id" {
  description = "ID of the S3 vocab bucket"
  value       = aws_s3_bucket.vocab_bucket.id
}

output "s3_vocab_bucket_arn" {
  description = "ARN of the S3 vocab bucket"
  value       = aws_s3_bucket.vocab_bucket.arn
}

output "dynamodb_user_table_name" {
  description = "Name of the DynamoDB user table"
  value       = aws_dynamodb_table.user_data.name
}

output "dynamodb_user_table_arn" {
  description = "ARN of the DynamoDB user table"
  value       = aws_dynamodb_table.user_data.arn
}

output "dynamodb_connections_table_name" {
  description = "Name of the DynamoDB connections table"
  value       = aws_dynamodb_table.connections.name
}

output "dynamodb_connections_table_arn" {
  description = "ARN of the DynamoDB connections table"
  value       = aws_dynamodb_table.connections.arn
}

output "dynamodb_vocab_table_name" {
  description = "Name of the DynamoDB vocab table"
  value       = aws_dynamodb_table.vocab_data.name
}

output "dynamodb_vocab_table_arn" {
  description = "ARN of the DynamoDB vocab table"
  value       = aws_dynamodb_table.vocab_data.arn
}

output "dynamodb_vocab_media_table_name" {
  description = "Name of the DynamoDB vocab media table"
  value       = aws_dynamodb_table.vocab_media.name
}

output "dynamodb_vocab_media_table_arn" {
  description = "ARN of the DynamoDB vocab media table"
  value       = aws_dynamodb_table.vocab_media.arn
}

output "dynamodb_vocab_list_table_name" {
  description = "Name of the DynamoDB vocab list table"
  value       = aws_dynamodb_table.vocab_list.name
}

output "dynamodb_vocab_list_table_arn" {
  description = "ARN of the DynamoDB vocab list table"
  value       = aws_dynamodb_table.vocab_list.arn
}

# Convenience output for all table ARNs
output "all_dynamodb_table_arns" {
  description = "List of all DynamoDB table ARNs"
  value = [
    aws_dynamodb_table.user_data.arn,
    aws_dynamodb_table.connections.arn,
    aws_dynamodb_table.vocab_data.arn,
    aws_dynamodb_table.vocab_media.arn,
    aws_dynamodb_table.vocab_list.arn
  ]
} 