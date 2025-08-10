output "ecs_cluster_id" {
  description = "ID of the ECS cluster"
  value       = aws_ecs_cluster.main.id
}

output "ecs_cluster_name" {
  description = "Name of the ECS cluster"
  value       = aws_ecs_cluster.main.name
}

output "ecs_cluster_arn" {
  description = "ARN of the ECS cluster"
  value       = aws_ecs_cluster.main.arn
}

output "frontend_service_name" {
  description = "Name of the frontend ECS service"
  value       = aws_ecs_service.frontend.name
}

output "backend_service_name" {
  description = "Name of the backend ECS service"
  value       = aws_ecs_service.backend.name
}

output "frontend_service_arn" {
  description = "ARN of the frontend ECS service"
  value       = aws_ecs_service.frontend.id
}

output "backend_service_arn" {
  description = "ARN of the backend ECS service"
  value       = aws_ecs_service.backend.id
}

output "ecs_frontend_task_execution_role_arn" {
  description = "ARN of the ECS frontend task execution role"
  value       = aws_iam_role.ecs_frontend_task_execution_role.arn
}

output "ecs_backend_task_execution_role_arn" {
  description = "ARN of the ECS backend task execution role"
  value       = aws_iam_role.ecs_backend_task_execution_role.arn
}

output "ecs_frontend_task_role_arn" {
  description = "ARN of the ECS frontend task role"
  value       = aws_iam_role.ecs_frontend_task_role.arn
}

output "ecs_backend_task_role_arn" {
  description = "ARN of the ECS backend task role"
  value       = aws_iam_role.ecs_backend_task_role.arn
}

output "ecs_task_role_arn" {
  description = "ARN of the ECS task role (backend) - deprecated, use specific role outputs"
  value       = aws_iam_role.ecs_backend_task_role.arn
}

output "frontend_task_definition_arn" {
  description = "ARN of the frontend task definition"
  value       = aws_ecs_task_definition.frontend.arn
}

output "backend_task_definition_arn" {
  description = "ARN of the backend task definition"
  value       = aws_ecs_task_definition.backend.arn
}

output "cluster_name" {
  description = "The name of the ECS cluster"
  value       = aws_ecs_cluster.main.name
} 