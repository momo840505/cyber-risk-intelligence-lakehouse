from __future__ import annotations

import os
from pathlib import Path

import boto3


BASE_DIR = Path(__file__).resolve().parents[1]


def _download_if_configured(
    bucket: str,
    key_env: str,
    destination: Path,
) -> None:
    key = os.getenv(key_env)
    if not key:
        return

    destination.parent.mkdir(parents=True, exist_ok=True)
    boto3.client("s3").download_file(bucket, key, str(destination))
    print(f"Downloaded s3://{bucket}/{key} -> {destination}")


def main() -> None:
    bucket = os.getenv("ARTIFACT_BUCKET")
    if not bucket:
        return

    database_path = Path(
        os.getenv(
            "ANALYTICS_DATABASE_PATH",
            BASE_DIR / "analytics" / "cyber_risk.duckdb",
        )
    )
    model_path = Path(
        os.getenv(
            "MODEL_PATH",
            BASE_DIR / "models" / "kev_horizon_ranker.joblib",
        )
    )
    metrics_path = Path(
        os.getenv(
            "MODEL_METRICS_PATH",
            BASE_DIR / "reports" / "model_metrics.json",
        )
    )

    _download_if_configured(bucket, "DATABASE_S3_KEY", database_path)
    _download_if_configured(bucket, "MODEL_S3_KEY", model_path)
    _download_if_configured(bucket, "MODEL_METRICS_S3_KEY", metrics_path)


if __name__ == "__main__":
    main()
