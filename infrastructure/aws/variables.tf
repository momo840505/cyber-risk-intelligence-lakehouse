variable "aws_region" {
  description = "AWS region used by the deployment template."
  type        = string
  default     = "ap-southeast-2"
}

variable "project_name" {
  description = "Project name used for AWS resource naming."
  type        = string
  default     = "cyber-risk-intelligence"
}

variable "environment" {
  description = "Deployment environment name."
  type        = string
  default     = "dev"
}

variable "vpc_cidr" {
  description = "CIDR block for the project VPC."
  type        = string
  default     = "10.20.0.0/16"
}

variable "public_subnet_count" {
  description = "Number of public subnets to create."
  type        = number
  default     = 2
}

variable "container_image" {
  description = "Container image URI for the FastAPI service. Replace this with the ECR image URI for real deployment."
  type        = string
  default     = "public.ecr.aws/docker/library/nginx:latest"
}

variable "app_port" {
  description = "Port exposed by the application container."
  type        = number
  default     = 8000
}

variable "desired_count" {
  description = "Desired number of ECS tasks."
  type        = number
  default     = 1
}

variable "container_cpu" {
  description = "CPU units for the ECS Fargate task."
  type        = number
  default     = 512
}

variable "container_memory" {
  description = "Memory in MiB for the ECS Fargate task."
  type        = number
  default     = 1024
}

variable "allowed_cidr_blocks" {
  description = "CIDR blocks allowed to access the public load balancer."
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "health_check_path" {
  description = "Health check path for the API service."
  type        = string
  default     = "/health"
}
