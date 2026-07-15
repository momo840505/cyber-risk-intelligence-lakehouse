provider "aws" {
  region = var.aws_region
}

locals {
  name_prefix    = "${var.project_name}-${var.environment}"
  container_name = "cyber-risk-api"

  common_tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "Terraform"
    Component   = "CyberRiskIntelligencePlatform"
  }
}

data "aws_availability_zones" "available" {
  state = "available"
}
