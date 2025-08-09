# WebSocket API
resource "aws_apigatewayv2_api" "websocket" {
  name                       = "${var.project_name}-vocab-processor-websocket"
  protocol_type              = "WEBSOCKET"
  description                = "WebSocket API for real-time vocab processing updates"
  route_selection_expression = "$request.body.action"

  tags = {
    Name        = "${var.project_name}-websocket-api"
    Environment = var.environment
    Project     = var.project_name
  }
}

# WebSocket Stage
resource "aws_apigatewayv2_stage" "production" {
  api_id      = aws_apigatewayv2_api.websocket.id
  name        = "prod"
  auto_deploy = true

  default_route_settings {
    throttling_rate_limit  = 100
    throttling_burst_limit = 50
  }

  tags = {
    Name        = "${var.project_name}-websocket-stage"
    Environment = var.environment
    Project     = var.project_name
  }
}

# IAM Role for WebSocket Lambda handlers
resource "aws_iam_role" "websocket_lambda" {
  name = "${var.project_name}-websocket-lambda-role"

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
    Name        = "${var.project_name}-websocket-lambda-role"
    Environment = var.environment
    Project     = var.project_name
  }
}

# Basic Lambda execution policy
resource "aws_iam_role_policy_attachment" "websocket_lambda_basic" {
  role       = aws_iam_role.websocket_lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# DynamoDB permissions for WebSocket handlers
resource "aws_iam_role_policy" "websocket_lambda_dynamodb" {
  name = "${var.project_name}-websocket-lambda-dynamodb-policy"
  role = aws_iam_role.websocket_lambda.id

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
          "dynamodb:Scan"
        ]
        Resource = [
          var.dynamodb_connections_table_arn,
          "${var.dynamodb_connections_table_arn}/index/*"
        ]
      }
    ]
  })
}

# API Gateway management permissions for WebSocket handlers
resource "aws_iam_role_policy" "websocket_lambda_apigateway" {
  name = "${var.project_name}-websocket-lambda-apigateway-policy"
  role = aws_iam_role.websocket_lambda.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "execute-api:ManageConnections"
        ]
        Resource = "arn:aws:execute-api:${var.aws_region}:${var.aws_account_id}:${aws_apigatewayv2_api.websocket.id}/*"
      }
    ]
  })
}

# CloudWatch Log Group for WebSocket Lambda handlers
resource "aws_cloudwatch_log_group" "websocket_lambda" {
  for_each = toset(["connect", "disconnect", "default"])

  name              = "/aws/lambda/${var.project_name}-websocket-${each.key}-handler"
  retention_in_days = 7

  tags = {
    Name        = "${var.project_name}-websocket-${each.key}-logs"
    Environment = var.environment
    Project     = var.project_name
  }
}

# Connect Handler Lambda Function
resource "aws_lambda_function" "connect_handler" {
  filename         = var.websocket_handler_zip_path
  function_name    = "${var.project_name}-websocket-connect-handler"
  role             = aws_iam_role.websocket_lambda.arn
  handler          = "websocket_handler.connect_handler"
  runtime          = "python3.12"
  memory_size      = 128
  timeout          = 30
  architectures    = ["arm64"]
  source_code_hash = filebase64sha256(var.websocket_handler_zip_path)

  layers = var.lambda_layer_arn != null ? [var.lambda_layer_arn] : []

  environment {
    variables = {
      DYNAMODB_CONNECTIONS_TABLE_NAME = var.dynamodb_connections_table_name
      WEBSOCKET_API_ENDPOINT          = "https://${aws_apigatewayv2_api.websocket.id}.execute-api.${var.aws_region}.amazonaws.com/prod"
    }
  }

  depends_on = [
    aws_iam_role_policy_attachment.websocket_lambda_basic,
    aws_cloudwatch_log_group.websocket_lambda["connect"],
  ]

  tags = {
    Name        = "${var.project_name}-websocket-connect-handler"
    Environment = var.environment
    Project     = var.project_name
  }
}

# Disconnect Handler Lambda Function
resource "aws_lambda_function" "disconnect_handler" {
  filename         = var.websocket_handler_zip_path
  function_name    = "${var.project_name}-websocket-disconnect-handler"
  role             = aws_iam_role.websocket_lambda.arn
  handler          = "websocket_handler.disconnect_handler"
  runtime          = "python3.12"
  memory_size      = 128
  timeout          = 30
  architectures    = ["arm64"]
  source_code_hash = filebase64sha256(var.websocket_handler_zip_path)

  layers = var.lambda_layer_arn != null ? [var.lambda_layer_arn] : []

  environment {
    variables = {
      DYNAMODB_CONNECTIONS_TABLE_NAME = var.dynamodb_connections_table_name
      WEBSOCKET_API_ENDPOINT          = "https://${aws_apigatewayv2_api.websocket.id}.execute-api.${var.aws_region}.amazonaws.com/prod"
    }
  }

  depends_on = [
    aws_iam_role_policy_attachment.websocket_lambda_basic,
    aws_cloudwatch_log_group.websocket_lambda["disconnect"],
  ]

  tags = {
    Name        = "${var.project_name}-websocket-disconnect-handler"
    Environment = var.environment
    Project     = var.project_name
  }
}

# Default Handler Lambda Function
resource "aws_lambda_function" "default_handler" {
  filename         = var.websocket_handler_zip_path
  function_name    = "${var.project_name}-websocket-default-handler"
  role             = aws_iam_role.websocket_lambda.arn
  handler          = "websocket_handler.default_handler"
  runtime          = "python3.12"
  memory_size      = 128
  timeout          = 30
  architectures    = ["arm64"]
  source_code_hash = filebase64sha256(var.websocket_handler_zip_path)

  layers = var.lambda_layer_arn != null ? [var.lambda_layer_arn] : []

  environment {
    variables = {
      DYNAMODB_CONNECTIONS_TABLE_NAME = var.dynamodb_connections_table_name
      WEBSOCKET_API_ENDPOINT          = "https://${aws_apigatewayv2_api.websocket.id}.execute-api.${var.aws_region}.amazonaws.com/prod"
    }
  }

  depends_on = [
    aws_iam_role_policy_attachment.websocket_lambda_basic,
    aws_cloudwatch_log_group.websocket_lambda["default"],
  ]

  tags = {
    Name        = "${var.project_name}-websocket-default-handler"
    Environment = var.environment
    Project     = var.project_name
  }
}

# Lambda permissions for API Gateway
resource "aws_lambda_permission" "connect_handler" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.connect_handler.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "arn:aws:execute-api:${var.aws_region}:${var.aws_account_id}:${aws_apigatewayv2_api.websocket.id}/*/*"
}

resource "aws_lambda_permission" "disconnect_handler" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.disconnect_handler.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "arn:aws:execute-api:${var.aws_region}:${var.aws_account_id}:${aws_apigatewayv2_api.websocket.id}/*/*"
}

resource "aws_lambda_permission" "default_handler" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.default_handler.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "arn:aws:execute-api:${var.aws_region}:${var.aws_account_id}:${aws_apigatewayv2_api.websocket.id}/*/*"
}

# WebSocket integrations
resource "aws_apigatewayv2_integration" "connect" {
  api_id           = aws_apigatewayv2_api.websocket.id
  integration_type = "AWS_PROXY"
  integration_uri  = aws_lambda_function.connect_handler.invoke_arn
}

resource "aws_apigatewayv2_integration" "disconnect" {
  api_id           = aws_apigatewayv2_api.websocket.id
  integration_type = "AWS_PROXY"
  integration_uri  = aws_lambda_function.disconnect_handler.invoke_arn
}

resource "aws_apigatewayv2_integration" "default" {
  api_id           = aws_apigatewayv2_api.websocket.id
  integration_type = "AWS_PROXY"
  integration_uri  = aws_lambda_function.default_handler.invoke_arn
}

# WebSocket routes
resource "aws_apigatewayv2_route" "connect" {
  api_id    = aws_apigatewayv2_api.websocket.id
  route_key = "$connect"
  target    = "integrations/${aws_apigatewayv2_integration.connect.id}"
}

resource "aws_apigatewayv2_route" "disconnect" {
  api_id    = aws_apigatewayv2_api.websocket.id
  route_key = "$disconnect"
  target    = "integrations/${aws_apigatewayv2_integration.disconnect.id}"
}

resource "aws_apigatewayv2_route" "default" {
  api_id    = aws_apigatewayv2_api.websocket.id
  route_key = "$default"
  target    = "integrations/${aws_apigatewayv2_integration.default.id}"
} 