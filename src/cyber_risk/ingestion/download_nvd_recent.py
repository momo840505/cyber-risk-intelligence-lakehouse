import json
import time
from datetime import datetime, timedelta, timezone
from typing import Any

from cyber_risk.config import NVD_BRONZE_DIR, NVD_CVE_API_URL, create_project_directories
from cyber_risk.ingestion.http_client import get_json


def save_jsonl(records: list[dict[str, Any]], output_path) -> None:
    with output_path.open("w", encoding="utf-8") as file:
        for record in records:
            file.write(json.dumps(record, ensure_ascii=False) + "\n")


def format_nvd_datetime(value: datetime) -> str:
    """
    Format datetime for NVD API.

    Example:
    2026-07-01T00:00:00.000Z
    """
    return value.strftime("%Y-%m-%dT%H:%M:%S.000Z")


def download_recent_nvd_cves(days_back: int = 30) -> None:
    """
    Download recently published CVEs from the NVD API.

    This first version limits the range to the last N days so that
    the project runs quickly while we are building the pipeline.
    """
    create_project_directories()

    end_datetime = datetime.now(timezone.utc)
    start_datetime = end_datetime - timedelta(days=days_back)

    downloaded_at = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    all_vulnerabilities: list[dict[str, Any]] = []
    start_index = 0
    results_per_page = 2000

    while True:
        params = {
            "pubStartDate": format_nvd_datetime(start_datetime),
            "pubEndDate": format_nvd_datetime(end_datetime),
            "resultsPerPage": results_per_page,
            "startIndex": start_index,
            "noRejected": "",
        }

        data = get_json(NVD_CVE_API_URL, params=params)

        vulnerabilities = data.get("vulnerabilities", [])
        total_results = data.get("totalResults", 0)

        all_vulnerabilities.extend(vulnerabilities)

        print(
            f"Downloaded page starting at {start_index}. "
            f"Page records: {len(vulnerabilities)}. "
            f"Total expected: {total_results}."
        )

        start_index += results_per_page

        if start_index >= total_results:
            break

        time.sleep(6)

    raw_output_path = NVD_BRONZE_DIR / f"nvd_recent_{days_back}_days_{downloaded_at}.json"
    jsonl_output_path = NVD_BRONZE_DIR / "nvd_recent_cves.jsonl"

    with raw_output_path.open("w", encoding="utf-8") as file:
        json.dump(all_vulnerabilities, file, indent=2, ensure_ascii=False)

    save_jsonl(all_vulnerabilities, jsonl_output_path)

    print(f"Downloaded NVD CVE records: {len(all_vulnerabilities)}")
    print(f"Saved raw file: {raw_output_path}")
    print(f"Saved JSONL file: {jsonl_output_path}")


if __name__ == "__main__":
    download_recent_nvd_cves(days_back=30)