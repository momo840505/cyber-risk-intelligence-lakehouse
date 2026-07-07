import json
from datetime import datetime, timezone

from cyber_risk.config import KEV_BRONZE_DIR, KEV_JSON_URL, create_project_directories
from cyber_risk.ingestion.http_client import get_json


def save_jsonl(records: list[dict], output_path) -> None:
    with output_path.open("w", encoding="utf-8") as file:
        for record in records:
            file.write(json.dumps(record, ensure_ascii=False) + "\n")


def download_kev_catalog() -> None:
    """
    Download CISA Known Exploited Vulnerabilities catalog.

    This is our ground-truth source for vulnerabilities that are
    known to have been exploited in the wild.
    """
    create_project_directories()

    downloaded_at = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    data = get_json(KEV_JSON_URL)

    raw_output_path = KEV_BRONZE_DIR / f"kev_catalog_{downloaded_at}.json"
    jsonl_output_path = KEV_BRONZE_DIR / "known_exploited_vulnerabilities.jsonl"

    with raw_output_path.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)

    vulnerabilities = data.get("vulnerabilities", [])
    save_jsonl(vulnerabilities, jsonl_output_path)

    print(f"Downloaded KEV catalog: {len(vulnerabilities)} records")
    print(f"Saved raw file: {raw_output_path}")
    print(f"Saved JSONL file: {jsonl_output_path}")


if __name__ == "__main__":
    download_kev_catalog()