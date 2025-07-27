output "pipeline_artifacts_bucket_name" {
  description = "Name of the pipeline artifacts S3 bucket"
  value       = aws_s3_bucket.pipeline_artifacts.bucket
}

output "frontend_pipeline_name" {
  description = "Name of the frontend CodePipeline"
  value       = aws_codepipeline.frontend.name
}

output "backend_pipeline_name" {
  description = "Name of the backend CodePipeline"
  value       = aws_codepipeline.backend.name
}



output "frontend_codebuild_project_name" {
  description = "Name of the frontend CodeBuild project"
  value       = aws_codebuild_project.frontend.name
}

output "backend_codebuild_project_name" {
  description = "Name of the backend CodeBuild project"
  value       = aws_codebuild_project.backend.name
}



output "codepipeline_role_arn" {
  description = "ARN of the CodePipeline service role"
  value       = aws_iam_role.codepipeline_role.arn
}

output "codebuild_role_arn" {
  description = "ARN of the CodeBuild service role"
  value       = aws_iam_role.codebuild_role.arn
} 