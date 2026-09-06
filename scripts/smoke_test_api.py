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
            if response.status != 200:
                raise RuntimeError(f"Unexpected status code: {response.status}")
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8")
        raise RuntimeError(f"Request failed: {url} status={error.code} body={body}") from error


def assert_condition(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    print(f"Base URL: {BASE_URL}")

    liveness = request_json("/livez")
    assert_condition(liveness["status"] == "ok", "Liveness check failed")
    print("PASS /livez")

    readiness = request_json("/readyz")
    assert_condition(readiness["status"] == "ok", "Readiness check failed")
    print("PASS /readyz")

    top_vulnerabilities = request_json("/vulnerabilities/top?limit=3")
    assert_condition(isinstance(top_vulnerabilities, list), "Top vulnerabilities response is not a list")
    assert_condition(len(top_vulnerabilities) > 0, "Top vulnerabilities response is empty")
    print("PASS /vulnerabilities/top")

    sample_cve_id = top_vulnerabilities[0]["cve_id"]
    remediation = request_json(f"/remediation/{sample_cve_id}")
    assert_condition(remediation["found"] is True, "Remediation lookup failed")
    assert_condition(bool(remediation["recommended_actions"]), "No remediation actions returned")
    print(f"PASS /remediation/{sample_cve_id}")

    metrics = request_json("/metrics")
    assert_condition("total_requests" in metrics, "Metrics response missing total_requests")
    print("PASS /metrics")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"Smoke test failed: {error}")
        sys.exit(1)
