# IAM Role for Lambda function
resource "aws_iam_role" "lambda" {
  name = "${var.project_name}-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name        = "${var.project_name}-lambda-role"
    Environment = var.environment
    Project     = var.project_name
  }
}

# Basic Lambda execution policy
resource "aws_iam_role_policy_attachment" "lambda_basic" {
  role       = aws_iam_role.lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# SSM read-only access for API keys
resource "aws_iam_role_policy_attachment" "lambda_ssm" {
  role       = aws_iam_role.lambda.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMReadOnlyAccess"
}

# SQS permissions
resource "aws_iam_role_policy" "lambda_sqs" {
  name = "${var.project_name}-lambda-sqs-policy"
  role = aws_iam_role.lambda.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "sqs:ReceiveMessage",
          "sqs:DeleteMessage",
          "sqs:GetQueueAttributes"
        ]
        Resource = var.sqs_queue_arn
      }
    ]
  })
}

# DynamoDB permissions
resource "aws_iam_role_policy" "lambda_dynamodb" {
  name = "${var.project_name}-lambda-dynamodb-policy"
  role = aws_iam_role.lambda.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:DeleteItem",
          "dynamodb:Query",
          "dynamodb:Scan",
          "dynamodb:BatchGetItem",
          "dynamodb:BatchWriteItem"
        ]
        Resource = [
          var.dynamodb_user_table_arn,
          var.dynamodb_vocab_table_arn,
          var.dynamodb_vocab_media_table_arn,
          var.dynamodb_connections_table_arn,
          "${var.dynamodb_user_table_arn}/index/*",
          "${var.dynamodb_vocab_table_arn}/index/*",
          "${var.dynamodb_vocab_media_table_arn}/index/*",
          "${var.dynamodb_connections_table_arn}/index/*"
        ]
      }
    ]
  })
}

# S3 permissions
resource "aws_iam_role_policy" "lambda_s3" {
  name = "${var.project_name}-lambda-s3-policy"
  role = aws_iam_role.lambda.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject"
        ]
        Resource = "${var.s3_bucket_arn}/*"
      },
      {
        Effect = "Allow"
        Action = [
          "s3:ListBucket"
        ]
        Resource = var.s3_bucket_arn
      }
    ]
  })
}

# WebSocket API permissions (if provided)
resource "aws_iam_role_policy" "lambda_websocket" {
  count = var.websocket_api_id != null ? 1 : 0

  name = "${var.project_name}-lambda-websocket-policy"
  role = aws_iam_role.lambda.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "execute-api:ManageConnections"
        ]
        Resource = "arn:aws:execute-api:${var.aws_region}:${var.aws_account_id}:${var.websocket_api_id}/*"
      }
    ]
  })
}

# Data sources to fetch API keys from Parameter Store
data "aws_ssm_parameter" "openai_api_key" {
  name = "/apikeys/DEFAULT_OPENAI_API_KEY"
}

data "aws_ssm_parameter" "pexels_api_key" {
  name = "/apikeys/PEXELS_API_KEY"
}

data "aws_ssm_parameter" "elevenlabs_api_key" {
  name = "/apikeys/ELEVENLABS_API_KEY"
}

# Lambda function for vocab processing
resource "aws_lambda_function" "vocab_processor" {
  filename         = var.lambda_function_zip_path
  function_name    = "${var.project_name}-vocab-processor"
  role             = aws_iam_role.lambda.arn
  handler          = "lambda_handler.lambda_handler"
  runtime          = "python3.12"
  memory_size      = 256
  timeout          = 120
  architectures    = ["arm64"]
  source_code_hash = filebase64sha256(var.lambda_function_zip_path)

  layers = [var.lambda_layer_arn]

  # No VPC config - Lambda runs in AWS managed network for internet access

  environment {
    variables = {
      # External API Keys from SSM Parameter Store
      OPENAI_API_KEY          = data.aws_ssm_parameter.openai_api_key.value
      PEXELS_API_KEY          = data.aws_ssm_parameter.pexels_api_key.value
      ELEVENLABS_API_KEY      = data.aws_ssm_parameter.elevenlabs_api_key.value
      AGENT_EXECUTION_CONTEXT = "lambda"

      # DynamoDB Tables
      DYNAMODB_USER_TABLE_NAME        = var.dynamodb_user_table_name
      DYNAMODB_VOCAB_TABLE_NAME       = var.dynamodb_vocab_table_name
      DYNAMODB_VOCAB_MEDIA_TABLE_NAME = var.dynamodb_vocab_media_table_name
      DYNAMODB_CONNECTIONS_TABLE_NAME = var.dynamodb_connections_table_name

      # S3 Bucket
      S3_MEDIA_BUCKET_NAME = var.s3_bucket_name

      # WebSocket API
      WEBSOCKET_API_ENDPOINT = var.websocket_api_endpoint
    }
  }

  depends_on = [
    aws_iam_role_policy_attachment.lambda_basic,
    aws_cloudwatch_log_group.lambda,
  ]

  tags = {
    Name        = "${var.project_name}-vocab-processor"
    Environment = var.environment
    Project     = var.project_name
  }
}

# CloudWatch Log Group for Lambda
resource "aws_cloudwatch_log_group" "lambda" {
  name              = "/aws/lambda/${var.project_name}-vocab-processor"
  retention_in_days = 7

  tags = {
    Name        = "${var.project_name}-lambda-logs"
    Environment = var.environment
    Project     = var.project_name
  }
}

# SQS Event Source for Lambda
resource "aws_lambda_event_source_mapping" "sqs" {
  event_source_arn = var.sqs_queue_arn
  function_name    = aws_lambda_function.vocab_processor.arn
} 