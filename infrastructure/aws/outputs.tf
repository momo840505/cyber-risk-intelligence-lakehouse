output "aws_region" {
  description = "AWS region used by this template."
  value       = var.aws_region
}

output "vpc_id" {
  description = "Created VPC ID."
  value       = aws_vpc.main.id
}

output "public_subnet_ids" {
  description = "Created public subnet IDs."
  value       = aws_subnet.public[*].id
}

output "lakehouse_bucket_name" {
  description = "S3 bucket for lakehouse storage."
  value       = aws_s3_bucket.lakehouse.bucket
}

output "ecr_repository_url" {
  description = "ECR repository URL for the API container."
  value       = aws_ecr_repository.api.repository_url
}

output "ecs_cluster_name" {
  description = "ECS cluster name."
  value       = aws_ecs_cluster.main.name
}

output "ecs_service_name" {
  description = "ECS service name."
  value       = aws_ecs_service.api.name
}

output "api_load_balancer_dns_name" {
  description = "Public DNS name of the API Application Load Balancer."
  value       = aws_lb.api.dns_name
}

output "api_url" {
  description = "HTTP URL for the deployed API."
  value       = "http://${aws_lb.api.dns_name}"
}

output "cloudwatch_log_group_name" {
  description = "CloudWatch log group for API container logs."
  value       = aws_cloudwatch_log_group.api.name
}
