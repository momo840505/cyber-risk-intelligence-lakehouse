# AWS deployment template

This directory contains the Terraform configuration for the API runtime. It is separate from the local PySpark pipeline: the pipeline produces the DuckDB database and trained model, while ECS serves those artifacts.

## What the template creates

- VPC and public subnets
- Application Load Balancer
- ECS Fargate service
- ECR repository
- S3 artifact bucket
- IAM roles
- CloudWatch logs and dashboard

The current template keeps ECS tasks in public subnets to avoid NAT Gateway cost in a portfolio environment. A production deployment would normally place application tasks in private subnets and terminate HTTPS at the ALB.

## Runtime artifact flow

The API image does not contain the database or trained model. They are versioned separately in S3.

```text
pipeline output
  ├─ analytics/cyber_risk.duckdb
  ├─ models/kev_horizon_ranker.joblib
  └─ reports/model_metrics.json
             │
             ▼
            S3
             │
             ▼
ECS task startup (task-role GetObject)
             │
             ▼
/app/analytics, /app/models, /app/reports
             │
             ▼
          FastAPI
```

The container entrypoint downloads the configured artifacts when `ARTIFACT_BUCKET` is set. The ALB checks `/readyz`; the target stays unhealthy until the database can be queried and the model can be loaded.

## Required image value

`container_image` has no default. Pass an immutable ECR image tag, preferably the Git commit SHA:

```hcl
container_image = "123456789012.dkr.ecr.ap-southeast-2.amazonaws.com/cyber-risk-intelligence-dev-api:020e029"
```

## Artifact keys

The defaults are:

```text
artifacts/analytics/cyber_risk.duckdb
artifacts/models/kev_horizon_ranker.joblib
artifacts/reports/model_metrics.json
```

Override them in `terraform.tfvars` if a different release layout is used.

## Validate locally

```powershell
terraform -chdir=infrastructure/aws fmt -recursive
terraform -chdir=infrastructure/aws init -backend=false
terraform -chdir=infrastructure/aws validate
```

The GitHub Actions workflow performs the same validation without creating resources.

## Deployment status

The Terraform configuration is validated in CI. It is intentionally not described as a live production deployment unless the resources have actually been applied and the runtime artifacts have been published to S3.

## Remaining production work

- HTTPS with ACM
- private ECS subnets and controlled egress
- API authentication/authorisation
- Secrets Manager or Parameter Store where secrets are introduced
- CloudWatch alarms
- autoscaling policy
- remote Terraform state with locking
- deployment workflow that publishes the image and artifacts together
