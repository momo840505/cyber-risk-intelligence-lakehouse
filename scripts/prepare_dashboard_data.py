"""Build the small Gold snapshot used by the hosted Streamlit dashboard."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_GOLD_DIR = PROJECT_ROOT / "data" / "gold"
SNAPSHOT_GOLD_DIR = PROJECT_ROOT / "app" / "data" / "gold"
METADATA_PATH = SNAPSHOT_GOLD_DIR / "_snapshot_metadata.json"

TABLES = [
    "vulnerability_priority",
    "vendor_risk_summary",
    "monthly_vulnerability_trends",
    "cwe_risk_summary",
]


def main() -> None:
    if not SOURCE_GOLD_DIR.exists():
        raise SystemExit(
            f"No Gold layer found at {SOURCE_GOLD_DIR}. Run scripts/run_pipeline.py first."
        )

    SNAPSHOT_GOLD_DIR.mkdir(parents=True, exist_ok=True)
    row_counts: dict[str, int] = {}
    min_published_date = None
    max_published_date = None

    for table_name in TABLES:
        source_path = SOURCE_GOLD_DIR / table_name
        if not source_path.exists():
            raise SystemExit(f"Missing Gold table: {source_path}")

        dataframe = pd.read_parquet(source_path)
        target_path = SNAPSHOT_GOLD_DIR / f"{table_name}.parquet"
        dataframe.to_parquet(target_path, index=False)
        row_counts[table_name] = int(len(dataframe))

        if table_name == "vulnerability_priority" and "published_date" in dataframe.columns:
            dates = pd.to_datetime(dataframe["published_date"], errors="coerce").dropna()
            if not dates.empty:
                min_published_date = dates.min().date().isoformat()
                max_published_date = dates.max().date().isoformat()

        print(f"{table_name}: {len(dataframe):,} rows -> {target_path}")

    metadata = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "published_date_min": min_published_date,
        "published_date_max": max_published_date,
        "row_counts": row_counts,
    }
    METADATA_PATH.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(f"Snapshot metadata -> {METADATA_PATH}")


if __name__ == "__main__":
    main()
