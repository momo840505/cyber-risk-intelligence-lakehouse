"""Prepare a small, git-committed snapshot of the Gold layer for the Streamlit Cloud dashboard.

The full lakehouse (data/bronze/, data/silver/, data/gold/) is intentionally gitignored:
it is PySpark output (many small partition files) and rebuilding it needs a JVM, which
Streamlit Community Cloud does not provide. Instead, this script reads the Gold tables you
already built locally (run scripts/run_pipeline.py first) and flattens each one into a
single parquet file under app/data/gold/ -- small enough to commit to git, and exactly
what app/dashboard.py reads at runtime, locally or once deployed.

Re-run this script and re-commit app/data/gold/ whenever you want the live dashboard to
reflect newer CVE data.

Usage:
    python scripts\\prepare_dashboard_data.py
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_GOLD_DIR = PROJECT_ROOT / "data" / "gold"
SNAPSHOT_GOLD_DIR = PROJECT_ROOT / "app" / "data" / "gold"

TABLES = [
    "vulnerability_priority",
    "vendor_risk_summary",
    "monthly_vulnerability_trends",
    "cwe_risk_summary",
]


def main() -> None:
    if not SOURCE_GOLD_DIR.exists():
        raise SystemExit(
            f"No Gold layer found at {SOURCE_GOLD_DIR}.\n"
            "Run the pipeline first:  python .\\scripts\\run_pipeline.py"
        )

    SNAPSHOT_GOLD_DIR.mkdir(parents=True, exist_ok=True)

    for table_name in TABLES:
        source_path = SOURCE_GOLD_DIR / table_name
        if not source_path.exists():
            raise SystemExit(
                f"Missing Gold table: {source_path}\n"
                "Run the pipeline first:  python .\\scripts\\run_pipeline.py"
            )

        dataframe = pd.read_parquet(source_path)
        target_path = SNAPSHOT_GOLD_DIR / f"{table_name}.parquet"
        dataframe.to_parquet(target_path, index=False)

        size_kb = target_path.stat().st_size / 1024
        print(f"{table_name}: {len(dataframe):,} rows -> {target_path} ({size_kb:.0f} KB)")

    print("\nDashboard snapshot ready.")
    print("Next: git add app/data/gold, commit, and push to update the live dashboard.")


if __name__ == "__main__":
    main()
