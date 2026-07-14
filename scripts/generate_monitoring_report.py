from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]

MONITORING_DIR = BASE_DIR / "monitoring"
REPORTS_DIR = BASE_DIR / "reports"

API_USAGE_LOG_PATH = MONITORING_DIR / "api_usage_log.csv"
ENDPOINT_SUMMARY_PATH = REPORTS_DIR / "api_endpoint_summary.csv"
MONITORING_SUMMARY_PATH = REPORTS_DIR / "api_monitoring_summary.json"


def load_api_log() -> pd.DataFrame:
    if not API_USAGE_LOG_PATH.exists():
        return pd.DataFrame(
            columns=[
                "timestamp_utc",
                "method",
                "path",
                "status_code",
                "response_time_ms",
                "client_host",
            ]
        )

    return pd.read_csv(API_USAGE_LOG_PATH)


def build_endpoint_summary(dataframe: pd.DataFrame) -> pd.DataFrame:
    if dataframe.empty:
        return pd.DataFrame(
            columns=[
                "path",
                "request_count",
                "error_count",
                "average_response_time_ms",
                "p95_response_time_ms",
            ]
        )

    dataframe["status_code"] = dataframe["status_code"].astype(int)
    dataframe["response_time_ms"] = dataframe["response_time_ms"].astype(float)
    dataframe["is_error"] = dataframe["status_code"] >= 400

    summary = (
        dataframe.groupby("path")
        .agg(
            request_count=("path", "size"),
            error_count=("is_error", "sum"),
            average_response_time_ms=("response_time_ms", "mean"),
            p95_response_time_ms=("response_time_ms", lambda values: values.quantile(0.95)),
        )
        .reset_index()
        .sort_values("request_count", ascending=False)
    )

    summary["average_response_time_ms"] = summary["average_response_time_ms"].round(3)
    summary["p95_response_time_ms"] = summary["p95_response_time_ms"].round(3)

    return summary


def build_monitoring_summary(dataframe: pd.DataFrame) -> dict:
    if dataframe.empty:
        return {
            "total_requests": 0,
            "error_count": 0,
            "error_rate": 0,
            "average_response_time_ms": 0,
            "p95_response_time_ms": 0,
            "unique_paths": 0,
            "first_request_utc": None,
            "last_request_utc": None,
        }

    dataframe["status_code"] = dataframe["status_code"].astype(int)
    dataframe["response_time_ms"] = dataframe["response_time_ms"].astype(float)

    total_requests = int(len(dataframe))
    error_count = int((dataframe["status_code"] >= 400).sum())

    return {
        "total_requests": total_requests,
        "error_count": error_count,
        "error_rate": round(error_count / total_requests, 4),
        "average_response_time_ms": round(float(dataframe["response_time_ms"].mean()), 3),
        "p95_response_time_ms": round(float(dataframe["response_time_ms"].quantile(0.95)), 3),
        "unique_paths": int(dataframe["path"].nunique()),
        "first_request_utc": str(dataframe["timestamp_utc"].iloc[0]),
        "last_request_utc": str(dataframe["timestamp_utc"].iloc[-1]),
    }


def main() -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    dataframe = load_api_log()
    endpoint_summary = build_endpoint_summary(dataframe)
    monitoring_summary = build_monitoring_summary(dataframe)

    endpoint_summary.to_csv(ENDPOINT_SUMMARY_PATH, index=False)

    MONITORING_SUMMARY_PATH.write_text(
        json.dumps(monitoring_summary, indent=2),
        encoding="utf-8",
    )

    print("\n========== API Monitoring Report ==========")
    print("\nEndpoint summary:")
    print(endpoint_summary.to_string(index=False))

    print("\nMonitoring summary:")
    print(json.dumps(monitoring_summary, indent=2))

    print(f"\nSaved endpoint summary: {ENDPOINT_SUMMARY_PATH}")
    print(f"Saved monitoring summary: {MONITORING_SUMMARY_PATH}")


if __name__ == "__main__":
    main()