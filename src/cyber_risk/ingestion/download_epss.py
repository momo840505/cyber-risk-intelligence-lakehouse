import csv
import gzip
import io
import json
from datetime import datetime, timezone

import requests

from cyber_risk.config import EPSS_BRONZE_DIR, create_project_directories


EPSS_CURRENT_CSV_URL = "https://epss.empiricalsecurity.com/epss_scores-current.csv.gz"


def download_epss_scores() -> None:
    create_project_directories()
    downloaded_at = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    response = requests.get(EPSS_CURRENT_CSV_URL, timeout=120, allow_redirects=True)
    response.raise_for_status()

    raw_output_path = EPSS_BRONZE_DIR / f"epss_scores_{downloaded_at}.csv.gz"
    raw_output_path.write_bytes(response.content)

    records = []
    with gzip.GzipFile(fileobj=io.BytesIO(response.content)) as compressed:
        with io.TextIOWrapper(compressed, encoding="utf-8") as text_stream:
            lines = (line for line in text_stream if not line.startswith("#"))
            reader = csv.DictReader(lines)
            for row in reader:
                cve_id = row.get("cve")
                if not cve_id:
                    continue
                records.append(
                    {
                        "cve": cve_id,
                        "epss": row.get("epss"),
                        "percentile": row.get("percentile"),
                        "date": datetime.now(timezone.utc).date().isoformat(),
                    }
                )

    jsonl_output_path = EPSS_BRONZE_DIR / "epss_top_scores.jsonl"
    with jsonl_output_path.open("w", encoding="utf-8") as file:
        for record in records:
            file.write(json.dumps(record) + "\n")

    print(f"Downloaded EPSS records: {len(records):,}")
    print(f"Saved raw file: {raw_output_path}")
    print(f"Saved JSONL file: {jsonl_output_path}")


def download_epss_top_scores(limit: int = 5000) -> None:
    """Compatibility wrapper for older scripts."""
    download_epss_scores()


if __name__ == "__main__":
    download_epss_scores()
