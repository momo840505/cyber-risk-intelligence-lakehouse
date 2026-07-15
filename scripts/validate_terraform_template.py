from __future__ import annotations

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
    "security_groups.tf": ["aws_security_group"],
    "storage.tf": ["aws_s3_bucket", "server_side_encryption"],
    "ecr.tf": ["aws_ecr_repository", "scan_on_push"],
    "iam.tf": ["aws_iam_role", "AmazonECSTaskExecutionRolePolicy"],
    "ecs.tf": ["aws_ecs_cluster", "aws_ecs_service", "aws_lb"],
    "monitoring.tf": ["aws_cloudwatch_dashboard"],
    "outputs.tf": ["api_url", "ecr_repository_url"],
}

FORBIDDEN_FILES = [
    "terraform.tfstate",
    "terraform.tfstate.backup",
    ".terraform.lock.hcl",
]


def assert_file_exists(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(f"Missing required file: {path}")

    if path.is_file() and path.stat().st_size == 0:
        raise ValueError(f"Required file is empty: {path}")


def assert_keywords(path: Path, keywords: list[str]) -> None:
    content = path.read_text(encoding="utf-8")

    missing_keywords = [
        keyword for keyword in keywords if keyword not in content
    ]

    if missing_keywords:
        raise ValueError(
            f"{path} is missing required keywords: {missing_keywords}"
        )


def main() -> None:
    print("\n========== Terraform Template Validation ==========")

    if not INFRA_DIR.exists():
        raise FileNotFoundError(f"Infrastructure directory missing: {INFRA_DIR}")

    for file_name in REQUIRED_FILES:
        path = INFRA_DIR / file_name
        assert_file_exists(path)
        print(f"PASS file exists: {path.relative_to(BASE_DIR)}")

    for file_name, keywords in REQUIRED_KEYWORDS.items():
        path = INFRA_DIR / file_name
        assert_keywords(path, keywords)
        print(f"PASS keywords: {path.relative_to(BASE_DIR)}")

    for file_name in FORBIDDEN_FILES:
        path = INFRA_DIR / file_name
        if path.exists():
            raise ValueError(
                f"Do not commit Terraform state or lock files: {path}"
            )

    print("\nTerraform template validation completed successfully.")


if __name__ == "__main__":
    main()
