# ECS Cluster
resource "aws_ecs_cluster" "main" {
  name = "${var.project_name}-cluster"

  setting {
    name  = "containerInsights"
    value = var.enable_container_insights ? "enabled" : "disabled"
  }

  tags = {
    Name        = "${var.project_name}-ecs-cluster"
    Environment = var.environment
    Project     = var.project_name
  }
}

# CloudWatch Log Groups
resource "aws_cloudwatch_log_group" "frontend" {
  name              = "/ecs/${var.project_name}-frontend"
  retention_in_days = var.log_retention_days

  tags = {
    Name        = "${var.project_name}-frontend-logs"
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_cloudwatch_log_group" "backend" {
  name              = "/ecs/${var.project_name}-backend"
  retention_in_days = var.log_retention_days

  tags = {
    Name        = "${var.project_name}-backend-logs"
    Environment = var.environment
    Project     = var.project_name
  }
}

# ECS Task Execution Role (Frontend)
resource "aws_iam_role" "ecs_frontend_task_execution_role" {
  name = "${var.project_name}-ecs-frontend-task-execution-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name        = "${var.project_name}-ecs-frontend-task-execution-role"
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_iam_role_policy_attachment" "ecs_frontend_task_execution_role_policy" {
  role       = aws_iam_role.ecs_frontend_task_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

## Backend ECS Task Execution Role
resource "aws_iam_role" "ecs_backend_task_execution_role" {
  name = "${var.project_name}-ecs-backend-task-execution-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name        = "${var.project_name}-ecs-backend-task-execution-role"
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_iam_role_policy_attachment" "ecs_backend_task_execution_role_policy" {
  role       = aws_iam_role.ecs_backend_task_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# Parameter Store and KMS decrypt permissions for backend execution only (scoped)
resource "aws_iam_role_policy" "ecs_backend_task_execution_parameter_store" {
  name = "${var.project_name}-ecs-backend-task-execution-parameter-store-policy"
  role = aws_iam_role.ecs_backend_task_execution_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = concat(
      length(local.backend_ssm_parameter_arns) > 0 ? [
        {
          Effect = "Allow"
          Action = [
            "ssm:GetParameters",
            "ssm:GetParameter"
          ]
          Resource = local.backend_ssm_parameter_arns
        }
      ] : [],
      [
        {
          Effect = "Allow"
          Action = [
            "kms:Decrypt"
          ]
          Resource = [
            "arn:aws:kms:${var.aws_region}:*:key/alias/aws/ssm"
          ]
        }
      ]
    )
  })
}

# Frontend ECS Task Role
resource "aws_iam_role" "ecs_frontend_task_role" {
  name = "${var.project_name}-ecs-frontend-task-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name        = "${var.project_name}-ecs-frontend-task-role"
    Environment = var.environment
    Project     = var.project_name
  }
}

# Backend ECS Task Role
resource "aws_iam_role" "ecs_backend_task_role" {
  name = "${var.project_name}-ecs-backend-task-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name        = "${var.project_name}-ecs-backend-task-role"
    Environment = var.environment
    Project     = var.project_name
  }
}

# DynamoDB permissions for backend only
resource "aws_iam_role_policy" "ecs_backend_dynamodb" {
  name = "${var.project_name}-ecs-backend-dynamodb-policy"
  role = aws_iam_role.ecs_backend_task_role.id

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
          "dynamodb:BatchWriteItem",
          "dynamodb:DescribeTable"
        ]
        Resource = concat(
          var.dynamodb_table_arns,
          [for arn in var.dynamodb_table_arns : "${arn}/index/*"]
        )
      }
    ]
  })
}

# S3 permissions for backend only
resource "aws_iam_role_policy" "ecs_backend_s3" {
  name = "${var.project_name}-ecs-backend-s3-policy"
  role = aws_iam_role.ecs_backend_task_role.id

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

# SQS permissions for backend only
resource "aws_iam_role_policy" "ecs_backend_sqs" {
  name = "${var.project_name}-ecs-backend-sqs-policy"
  role = aws_iam_role.ecs_backend_task_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "sqs:SendMessage",
          "sqs:GetQueueAttributes"
        ]
        Resource = var.sqs_queue_arn
      }
    ]
  })
}

# SES permissions for backend only
resource "aws_iam_role_policy" "ecs_backend_ses" {
  name = "${var.project_name}-ecs-backend-ses-policy"
  role = aws_iam_role.ecs_backend_task_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ses:SendEmail",
          "ses:SendRawEmail"
        ]
        Resource = [
          "arn:aws:ses:${var.aws_region}:*:identity/*"
        ]
      }
    ]
  })
}

# Frontend Task Definition
resource "aws_ecs_task_definition" "frontend" {
  family                   = "${var.project_name}-frontend"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.frontend_cpu
  memory                   = var.frontend_memory
  execution_role_arn       = aws_iam_role.ecs_frontend_task_execution_role.arn
  task_role_arn            = aws_iam_role.ecs_frontend_task_role.arn

  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture        = "ARM64"
  }

  container_definitions = jsonencode([
    {
      name  = "frontend"
      image = var.frontend_image_uri
      portMappings = [
        {
          containerPort = 80
          protocol      = "tcp"
        }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.frontend.name
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "ecs"
        }
      }
      essential = true
    }
  ])

  tags = {
    Name        = "${var.project_name}-frontend-task-definition"
    Environment = var.environment
    Project     = var.project_name
  }
}

# Backend Task Definition
resource "aws_ecs_task_definition" "backend" {
  family                   = "${var.project_name}-backend"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.backend_cpu
  memory                   = var.backend_memory
  execution_role_arn       = aws_iam_role.ecs_backend_task_execution_role.arn
  task_role_arn            = aws_iam_role.ecs_backend_task_role.arn

  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture        = "ARM64"
  }

  container_definitions = jsonencode([
    {
      name  = "backend"
      image = var.backend_image_uri
      portMappings = [
        {
          containerPort = 8080
          protocol      = "tcp"
        }
      ]
      environment = local.backend_environment_variables
      secrets     = local.backend_secrets
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.backend.name
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "ecs"
        }
      }
      essential = true
    }
  ])

  tags = {
    Name        = "${var.project_name}-backend-task-definition"
    Environment = var.environment
    Project     = var.project_name
  }
}

data "aws_ssm_parameter" "backend" {
  for_each        = var.backend_ssm_parameter_paths
  name            = each.value
  with_decryption = true
}

locals {
  backend_environment_variables = [
    for k in sort(keys(var.backend_env_map)) : {
      name  = k
      value = var.backend_env_map[k]
    }
  ]

  backend_secrets = [
    for k in sort(keys(var.backend_ssm_parameter_paths)) : {
      name      = k
      valueFrom = data.aws_ssm_parameter.backend[k].arn
    }
  ]

  backend_ssm_parameter_arns = [
    for k in sort(keys(var.backend_ssm_parameter_paths)) : data.aws_ssm_parameter.backend[k].arn
  ]
}

# Frontend ECS Service
resource "aws_ecs_service" "frontend" {
  name            = "${var.project_name}-frontend"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.frontend.arn
  desired_count   = var.desired_count
  launch_type     = "FARGATE"

  network_configuration {
    security_groups  = [var.ecs_tasks_security_group_id]
    subnets          = var.public_subnet_ids
    assign_public_ip = true # In public subnets as requested
  }

  load_balancer {
    target_group_arn = var.frontend_target_group_arn
    container_name   = "frontend"
    container_port   = 80
  }

  deployment_controller {
    type = "ECS"
  }

  depends_on = [var.alb_listener_arn]

  tags = {
    Name        = "${var.project_name}-frontend-service"
    Environment = var.environment
    Project     = var.project_name
  }
}

# Backend ECS Service
resource "aws_ecs_service" "backend" {
  name            = "${var.project_name}-backend"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.backend.arn
  desired_count   = var.desired_count
  launch_type     = "FARGATE"

  network_configuration {
    security_groups  = [var.ecs_tasks_security_group_id]
    subnets          = var.public_subnet_ids
    assign_public_ip = true # In public subnets as requested
  }

  load_balancer {
    target_group_arn = var.backend_target_group_arn
    container_name   = "backend"
    container_port   = 8080
  }

  deployment_controller {
    type = "ECS"
  }

  depends_on = [var.alb_listener_arn]

  tags = {
    Name        = "${var.project_name}-backend-service"
    Environment = var.environment
    Project     = var.project_name
  }
} 