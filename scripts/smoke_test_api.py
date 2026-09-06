from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request


BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8001")


def request_json(path: str) -> dict | list:
    url = f"{BASE_URL}{path}"

    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            status_code = response.status
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8")
        raise RuntimeError(f"Request failed: {url} status={error.code} body={body}") from error
    except Exception as error:
        raise RuntimeError(f"Request failed: {url} error={error}") from error

    if status_code != 200:
        raise RuntimeError(f"Unexpected status code: {url} status={status_code}")

    return json.loads(body)


def assert_condition(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    print("\n========== API Smoke Test ==========")
    print(f"Base URL: {BASE_URL}")

    health = request_json("/health")
    assert_condition(health["status"] == "ok", "Health status is not ok")
    assert_condition(health["analytics_database_exists"] is True, "Analytics database is missing")
    assert_condition(health["model_exists"] is True, "ML model is missing")
    print("PASS /health")

    top_vulnerabilities = request_json("/vulnerabilities/top?limit=3")
    assert_condition(isinstance(top_vulnerabilities, list), "Top vulnerabilities response is not a list")
    assert_condition(len(top_vulnerabilities) > 0, "Top vulnerabilities response is empty")
    print("PASS /vulnerabilities/top")

    # Pull a real, currently-ingested CVE ID from the API instead of hardcoding
    # one. NVD ingestion only keeps a rolling 30-day window (see README
    # "Limitations"), so a fixed CVE ID here would silently start failing
    # the moment that CVE rolls out of the dataset on a later pipeline run.
    sample_cve_id = top_vulnerabilities[0]["cve_id"]

    remediation = request_json(f"/remediation/{sample_cve_id}")
    assert_condition(remediation["found"] is True, f"Remediation CVE was not found: {sample_cve_id}")
    assert_condition(len(remediation["recommended_actions"]) > 0, "No remediation actions returned")
    print(f"PASS /remediation/{sample_cve_id}")

    metrics = request_json("/metrics")
    assert_condition("total_requests" in metrics, "Metrics response missing total_requests")
    assert_condition("requests_by_path" in metrics, "Metrics response missing requests_by_path")
    print("PASS /metrics")

    print("\nAll smoke tests passed.")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"\nSmoke test failed: {error}")
        sys.exit(1)
