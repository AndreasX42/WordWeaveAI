# Dead Letter Queue (FIFO)
resource "aws_sqs_queue" "vocab_jobs_dlq" {
  name                        = "${var.project_name}-vocab-jobs-dlq.fifo"
  fifo_queue                  = true
  content_based_deduplication = false

  # SQS managed encryption
  sqs_managed_sse_enabled = true

  tags = {
    Name        = "${var.project_name}-vocab-jobs-dlq"
    Environment = var.environment
    Project     = var.project_name
  }
}

# Main FIFO Queue
resource "aws_sqs_queue" "vocab_jobs_queue" {
  name                        = "${var.project_name}-vocab-jobs-queue.fifo"
  fifo_queue                  = true
  content_based_deduplication = false
  visibility_timeout_seconds  = 150

  # SQS managed encryption
  sqs_managed_sse_enabled = true

  # Dead letter queue configuration
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.vocab_jobs_dlq.arn
    maxReceiveCount     = 1
  })

  tags = {
    Name        = "${var.project_name}-vocab-jobs-queue"
    Environment = var.environment
    Project     = var.project_name
  }
} 