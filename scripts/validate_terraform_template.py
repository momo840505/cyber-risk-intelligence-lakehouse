from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
INFRA_DIR = BASE_DIR / "infrastructure" / "aws"

REQUIRED_FILES = [
    "README.md",
    "versions.tf",
    "variables.tf",
    "main.tf",
    "networking.tf",
    "security_groups.tf",
    "storage.tf",
    "ecr.tf",
    "iam.tf",
    "ecs.tf",
    "monitoring.tf",
    "outputs.tf",
    "terraform.tfvars.example",
]

REQUIRED_KEYWORDS = {
    "versions.tf": ["required_providers", "hashicorp/aws"],
    "networking.tf": ["aws_vpc", "aws_subnet", "aws_internet_gateway"],
    "storage.tf": ["aws_s3_bucket", "server_side_encryption"],
    "ecr.tf": ["aws_ecr_repository", "IMMUTABLE", "scan_on_push"],
    "iam.tf": ["aws_iam_role", "s3:GetObject"],
    "variables.tf": ["health_check_path", "/readyz"],
    "ecs.tf": ["aws_ecs_cluster", "aws_ecs_service", "ARTIFACT_BUCKET", "health_check_path"],
    "monitoring.tf": ["aws_cloudwatch_dashboard"],
    "outputs.tf": ["api_url", "ecr_repository_url"],
}

FORBIDDEN_FILES = ["terraform.tfstate", "terraform.tfstate.backup"]


def main() -> None:
    if not INFRA_DIR.exists():
        raise FileNotFoundError(f"Infrastructure directory missing: {INFRA_DIR}")

    for file_name in REQUIRED_FILES:
        path = INFRA_DIR / file_name
        if not path.exists() or path.stat().st_size == 0:
            raise FileNotFoundError(f"Missing or empty required file: {path}")

    for file_name, keywords in REQUIRED_KEYWORDS.items():
        content = (INFRA_DIR / file_name).read_text(encoding="utf-8")
        missing = [keyword for keyword in keywords if keyword not in content]
        if missing:
            raise ValueError(f"{file_name} is missing required keywords: {missing}")

    for file_name in FORBIDDEN_FILES:
        if (INFRA_DIR / file_name).exists():
            raise ValueError(f"Do not commit Terraform state: {file_name}")

    print("Terraform template validation completed successfully.")


if __name__ == "__main__":
    main()
