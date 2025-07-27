# S3 Bucket for vocab data storage
resource "aws_s3_bucket" "vocab_bucket" {
  bucket        = var.s3_media_bucket_name
  force_destroy = true

  tags = {
    Name        = "${var.project_name}-vocab-bucket"
    Environment = var.environment
    Project     = var.project_name
  }
}

# S3 Bucket versioning
resource "aws_s3_bucket_versioning" "vocab_bucket" {
  bucket = aws_s3_bucket.vocab_bucket.id
  versioning_configuration {
    status = "Enabled"
  }
}

# S3 Bucket encryption
resource "aws_s3_bucket_server_side_encryption_configuration" "vocab_bucket" {
  bucket = aws_s3_bucket.vocab_bucket.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# S3 Bucket public access block
resource "aws_s3_bucket_public_access_block" "vocab_bucket" {
  bucket = aws_s3_bucket.vocab_bucket.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# DynamoDB table for user data
resource "aws_dynamodb_table" "user_data" {
  name         = var.dynamodb_user_table_name
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "user_id"

  attribute {
    name = "user_id"
    type = "S"
  }

  attribute {
    name = "email"
    type = "S"
  }

  attribute {
    name = "username"
    type = "S"
  }

  attribute {
    name = "google_id"
    type = "S"
  }

  # EmailIndex
  global_secondary_index {
    name            = "EmailIndex"
    hash_key        = "email"
    projection_type = "ALL"
  }

  # UsernameIndex
  global_secondary_index {
    name            = "UsernameIndex"
    hash_key        = "username"
    projection_type = "ALL"
  }

  # GoogleIDIndex
  global_secondary_index {
    name            = "GoogleIDIndex"
    hash_key        = "google_id"
    projection_type = "ALL"
  }

  server_side_encryption {
    enabled = true
  }

  tags = {
    Name        = "${var.project_name}-user-data-table"
    Environment = var.environment
    Project     = var.project_name
  }
}

# DynamoDB table for WebSocket connections
resource "aws_dynamodb_table" "connections" {
  name         = var.dynamodb_connections_table_name
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "connection_id"

  attribute {
    name = "connection_id"
    type = "S"
  }

  attribute {
    name = "user_id"
    type = "S"
  }

  attribute {
    name = "connected_at"
    type = "S"
  }

  attribute {
    name = "vocab_word"
    type = "S"
  }

  # UserConnectionsIndex
  global_secondary_index {
    name            = "UserConnectionsIndex"
    hash_key        = "user_id"
    range_key       = "connected_at"
    projection_type = "ALL"
  }

  # VocabWordConnectionsIndex
  global_secondary_index {
    name            = "VocabWordConnectionsIndex"
    hash_key        = "vocab_word"
    projection_type = "ALL"
  }

  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  server_side_encryption {
    enabled = true
  }

  tags = {
    Name        = "${var.project_name}-connections-table"
    Environment = var.environment
    Project     = var.project_name
  }
}

# DynamoDB table for vocab data with composite key design
resource "aws_dynamodb_table" "vocab_data" {
  name         = var.dynamodb_vocab_table_name
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "PK"
  range_key    = "SK"

  attribute {
    name = "PK"
    type = "S"
  }

  attribute {
    name = "SK"
    type = "S"
  }

  attribute {
    name = "LKP"
    type = "S"
  }

  attribute {
    name = "SRC_LANG"
    type = "S"
  }

  attribute {
    name = "english_word"
    type = "S"
  }

  # ReverseLookupIndex
  global_secondary_index {
    name            = "ReverseLookupIndex"
    hash_key        = "LKP"
    range_key       = "SRC_LANG"
    projection_type = "INCLUDE"
    non_key_attributes = [
      "source_word",
      "target_word",
      "source_language",
      "target_language",
      "source_pos",
      "media_ref"
    ]
  }

  # EnglishMediaLookupIndex
  global_secondary_index {
    name            = "EnglishMediaLookupIndex"
    hash_key        = "english_word"
    projection_type = "INCLUDE"
    non_key_attributes = [
      "source_word",
      "target_word",
      "source_language",
      "target_language",
      "source_pos",
      "media_ref"
    ]
  }

  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  point_in_time_recovery {
    enabled = false
  }

  server_side_encryption {
    enabled = true
  }

  tags = {
    Name        = "${var.project_name}-vocab-data-table"
    Environment = var.environment
    Project     = var.project_name
  }
}

# DynamoDB table for vocab media data
resource "aws_dynamodb_table" "vocab_media" {
  name         = var.dynamodb_vocab_media_table_name
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "PK"

  attribute {
    name = "PK"
    type = "S"
  }

  server_side_encryption {
    enabled = true
  }

  tags = {
    Name        = "${var.project_name}-vocab-media-table"
    Environment = var.environment
    Project     = var.project_name
  }
}

# DynamoDB table for vocab list data
resource "aws_dynamodb_table" "vocab_list" {
  name         = var.dynamodb_vocab_list_table_name
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "PK"
  range_key    = "SK"

  attribute {
    name = "PK"
    type = "S"
  }

  attribute {
    name = "SK"
    type = "S"
  }

  server_side_encryption {
    enabled = true
  }

  tags = {
    Name        = "${var.project_name}-vocab-list-table"
    Environment = var.environment
    Project     = var.project_name
  }
} 