output "websocket_api_id" {
  description = "ID of the WebSocket API"
  value       = aws_apigatewayv2_api.websocket.id
}

output "websocket_api_endpoint" {
  description = "WebSocket API endpoint URL"
  value       = "https://${aws_apigatewayv2_api.websocket.id}.execute-api.${var.aws_region}.amazonaws.com/prod"
}

output "connect_handler_function_name" {
  description = "Name of the connect handler function"
  value       = aws_lambda_function.connect_handler.function_name
}

output "disconnect_handler_function_name" {
  description = "Name of the disconnect handler function"
  value       = aws_lambda_function.disconnect_handler.function_name
}

output "default_handler_function_name" {
  description = "Name of the default handler function"
  value       = aws_lambda_function.default_handler.function_name
}

output "websocket_lambda_role_arn" {
  description = "ARN of the WebSocket Lambda IAM role"
  value       = aws_iam_role.websocket_lambda.arn
} 