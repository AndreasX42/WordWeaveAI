# S3 bucket for Lambda layer artifacts
resource "random_id" "bucket_suffix" {
  byte_length = 4
}

resource "aws_s3_bucket" "lambda_layer_artifacts" {
  bucket        = "${var.project_name}-lambda-layer-artifacts-${random_id.bucket_suffix.hex}"
  force_destroy = true

  tags = {
    Name        = "${var.project_name}-lambda-layer-artifacts"
    Environment = var.environment
    Project     = var.project_name
  }
}

# Upload layer ZIP to S3
resource "aws_s3_object" "lambda_layer" {
  bucket = aws_s3_bucket.lambda_layer_artifacts.id
  key    = "lambda-layer.zip"
  source = var.lambda_layer_zip_path
  etag   = filemd5(var.lambda_layer_zip_path)

  tags = {
    Name        = "${var.project_name}-lambda-layer"
    Environment = var.environment
    Project     = var.project_name
  }
}

# Lambda layer version
resource "aws_lambda_layer_version" "requirements" {
  layer_name          = "${var.project_name}-requirements"
  s3_bucket           = aws_s3_bucket.lambda_layer_artifacts.id
  s3_key              = aws_s3_object.lambda_layer.key
  compatible_runtimes = ["python3.12"]
  source_code_hash    = filebase64sha256(var.lambda_layer_zip_path)

  lifecycle {
    create_before_destroy = true
  }
} 