import json
from datetime import datetime, timezone

from cyber_risk.config import EPSS_API_URL, EPSS_BRONZE_DIR, create_project_directories
from cyber_risk.ingestion.http_client import get_json


def save_jsonl(records: list[dict], output_path) -> None:
    with output_path.open("w", encoding="utf-8") as file:
        for record in records:
            file.write(json.dumps(record, ensure_ascii=False) + "\n")


def download_epss_top_scores(limit: int = 5000) -> None:
    """
    Download top EPSS scores.

    For the first version, we download top CVEs by EPSS probability.
    Later, we can replace this with the full daily EPSS CSV file.
    """
    create_project_directories()

    downloaded_at = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    params = {
        "order": "!epss",
        "limit": limit,
    }

    data = get_json(EPSS_API_URL, params=params)

    raw_output_path = EPSS_BRONZE_DIR / f"epss_top_{limit}_{downloaded_at}.json"
    jsonl_output_path = EPSS_BRONZE_DIR / "epss_top_scores.jsonl"

    with raw_output_path.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)

    records = data.get("data", [])
    save_jsonl(records, jsonl_output_path)

    print(f"Downloaded EPSS records: {len(records)}")
    print(f"Saved raw file: {raw_output_path}")
    print(f"Saved JSONL file: {jsonl_output_path}")


if __name__ == "__main__":
    download_epss_top_scores()