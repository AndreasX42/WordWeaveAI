output "queue_id" {
  description = "ID of the SQS queue"
  value       = aws_sqs_queue.vocab_jobs_queue.id
}

output "queue_arn" {
  description = "ARN of the SQS queue"
  value       = aws_sqs_queue.vocab_jobs_queue.arn
}

output "queue_url" {
  description = "URL of the SQS queue"
  value       = aws_sqs_queue.vocab_jobs_queue.url
}

output "dlq_id" {
  description = "ID of the SQS dead letter queue"
  value       = aws_sqs_queue.vocab_jobs_dlq.id
}

output "dlq_arn" {
  description = "ARN of the SQS dead letter queue"
  value       = aws_sqs_queue.vocab_jobs_dlq.arn
}

output "dlq_url" {
  description = "URL of the SQS dead letter queue"
  value       = aws_sqs_queue.vocab_jobs_dlq.url
} 