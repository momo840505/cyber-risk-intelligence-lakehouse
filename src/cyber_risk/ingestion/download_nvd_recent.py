import json
import os
import time
from datetime import datetime, timedelta, timezone
from typing import Any

from cyber_risk.config import NVD_BRONZE_DIR, NVD_CVE_API_URL, create_project_directories
from cyber_risk.ingestion.http_client import get_json


MAX_NVD_RANGE_DAYS = 120
RESULTS_PER_PAGE = 2000


def save_jsonl(records: list[dict[str, Any]], output_path) -> None:
    with output_path.open("w", encoding="utf-8") as file:
        for record in records:
            file.write(json.dumps(record, ensure_ascii=False) + "\n")


def format_nvd_datetime(value: datetime) -> str:
    return value.strftime("%Y-%m-%dT%H:%M:%S.000Z")


def iter_windows(start_datetime: datetime, end_datetime: datetime):
    cursor = start_datetime
    while cursor < end_datetime:
        window_end = min(cursor + timedelta(days=MAX_NVD_RANGE_DAYS), end_datetime)
        yield cursor, window_end
        cursor = window_end + timedelta(milliseconds=1)


def download_nvd_range(start_datetime: datetime, end_datetime: datetime) -> list[dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}

    for window_start, window_end in iter_windows(start_datetime, end_datetime):
        start_index = 0
        while True:
            params = {
                "pubStartDate": format_nvd_datetime(window_start),
                "pubEndDate": format_nvd_datetime(window_end),
                "resultsPerPage": RESULTS_PER_PAGE,
                "startIndex": start_index,
                "noRejected": "",
            }
            data = get_json(NVD_CVE_API_URL, params=params)
            vulnerabilities = data.get("vulnerabilities", [])
            total_results = int(data.get("totalResults", 0))

            for item in vulnerabilities:
                cve_id = item.get("cve", {}).get("id")
                if cve_id:
                    records[cve_id] = item

            print(
                f"NVD {window_start.date()} to {window_end.date()}: "
                f"{min(start_index + len(vulnerabilities), total_results):,}/{total_results:,}"
            )

            start_index += RESULTS_PER_PAGE
            if start_index >= total_results:
                break
            time.sleep(6)

        time.sleep(6)

    return list(records.values())


def download_recent_nvd_cves(days_back: int | None = None) -> None:
    create_project_directories()

    if days_back is None:
        days_back = int(os.getenv("NVD_DAYS_BACK", "730"))
    if days_back < 1:
        raise ValueError("days_back must be positive")

    end_datetime = datetime.now(timezone.utc)
    start_datetime = end_datetime - timedelta(days=days_back)
    downloaded_at = end_datetime.strftime("%Y%m%dT%H%M%SZ")

    vulnerabilities = download_nvd_range(start_datetime, end_datetime)

    raw_output_path = NVD_BRONZE_DIR / f"nvd_{days_back}_days_{downloaded_at}.json"
    jsonl_output_path = NVD_BRONZE_DIR / "nvd_recent_cves.jsonl"

    with raw_output_path.open("w", encoding="utf-8") as file:
        json.dump(vulnerabilities, file, ensure_ascii=False)

    save_jsonl(vulnerabilities, jsonl_output_path)
    print(f"Downloaded NVD CVE records: {len(vulnerabilities):,}")
    print(f"Saved JSONL file: {jsonl_output_path}")


if __name__ == "__main__":
    download_recent_nvd_cves()
