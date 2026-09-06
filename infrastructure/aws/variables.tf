variable "aws_region" {
  description = "AWS region for the deployment."
  type        = string
  default     = "ap-southeast-2"
}

variable "project_name" {
  description = "Project name used in resource names."
  type        = string
  default     = "cyber-risk-intelligence"
}

variable "environment" {
  description = "Deployment environment."
  type        = string
  default     = "dev"
}

variable "vpc_cidr" {
  description = "CIDR block for the VPC."
  type        = string
  default     = "10.20.0.0/16"
}

variable "public_subnet_count" {
  description = "Number of public subnets."
  type        = number
  default     = 2
}

variable "container_image" {
  description = "ECR image URI for the FastAPI service."
  type        = string
}

variable "app_port" {
  description = "Application port in the container."
  type        = number
  default     = 8000
}

variable "desired_count" {
  description = "Number of ECS tasks."
  type        = number
  default     = 1
}

variable "container_cpu" {
  description = "CPU units for the Fargate task."
  type        = number
  default     = 512
}

variable "container_memory" {
  description = "Memory in MiB for the Fargate task."
  type        = number
  default     = 1024
}

variable "allowed_cidr_blocks" {
  description = "CIDR blocks allowed to reach the public ALB."
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "health_check_path" {
  description = "Readiness endpoint used by the ALB target group."
  type        = string
  default     = "/readyz"
}

variable "database_s3_key" {
  description = "S3 key for the DuckDB analytics database."
  type        = string
  default     = "artifacts/analytics/cyber_risk.duckdb"
}

variable "model_s3_key" {
  description = "S3 key for the trained model artifact."
  type        = string
  default     = "artifacts/models/kev_horizon_ranker.joblib"
}

variable "model_metrics_s3_key" {
  description = "S3 key for the model metrics JSON used by the API threshold."
  type        = string
  default     = "artifacts/reports/model_metrics.json"
}
