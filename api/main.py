from __future__ import annotations

import csv
import time
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Optional

import duckdb
import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException, Query, Request
from pydantic import BaseModel, Field

from rag.remediation_copilot import generate_remediation_plan


BASE_DIR = Path(__file__).resolve().parents[1]

ANALYTICS_DATABASE_PATH = BASE_DIR / "analytics" / "cyber_risk.duckdb"
MODEL_PATH = BASE_DIR / "models" / "priority_classifier.joblib"
MONITORING_DIR = BASE_DIR / "monitoring"
API_USAGE_LOG_PATH = MONITORING_DIR / "api_usage_log.csv"

LOG_LOCK = Lock()

API_LOG_COLUMNS = [
    "timestamp_utc",
    "method",
    "path",
    "status_code",
    "response_time_ms",
    "client_host",
]


app = FastAPI(
    title="Cyber Risk Intelligence API",
    description=(
        "FastAPI service for querying cyber risk lakehouse marts, "
        "predicting vulnerability priority, and generating RAG-based "
        "remediation guidance."
    ),
    version="2.0.0",
)


class PriorityPredictionRequest(BaseModel):
    cvss_base_score: float = Field(..., ge=0, le=10)
    epss_score: Optional[float] = Field(default=0, ge=0, le=1)
    epss_percentile: Optional[float] = Field(default=0, ge=0, le=1)
    is_known_exploited: int = Field(..., ge=0, le=1)
    reference_count: int = Field(default=0, ge=0)
    affected_entry_count: int = Field(default=0, ge=0)
    published_month: int = Field(..., ge=1, le=12)
    cvss_base_severity: str = Field(default="UNKNOWN")
    attack_vector: str = Field(default="UNKNOWN")
    attack_complexity: str = Field(default="UNKNOWN")
    privileges_required: str = Field(default="UNKNOWN")
    user_interaction: str = Field(default="UNKNOWN")
    cwe_id: str = Field(default="UNKNOWN")


def validate_database_exists() -> None:
    if not ANALYTICS_DATABASE_PATH.exists():
        raise HTTPException(
            status_code=500,
            detail=(
                "Analytics database not found. "
                "Run python scripts/run_dbt.py before starting the API."
            ),
        )


def run_query(query: str, parameters: Optional[list] = None) -> list[dict]:
    validate_database_exists()

    with duckdb.connect(str(ANALYTICS_DATABASE_PATH), read_only=True) as connection:
        dataframe = connection.execute(query, parameters or []).fetchdf()

    return dataframe.to_dict(orient="records")


def load_model():
    if not MODEL_PATH.exists():
        raise HTTPException(
            status_code=500,
            detail=(
                "ML model not found. "
                "Run python scripts/run_ml.py before using prediction endpoint."
            ),
        )

    return joblib.load(MODEL_PATH)


def append_api_log(
    method: str,
    path: str,
    status_code: int,
    response_time_ms: float,
    client_host: str,
) -> None:
    MONITORING_DIR.mkdir(parents=True, exist_ok=True)

    row = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "method": method,
        "path": path,
        "status_code": status_code,
        "response_time_ms": round(response_time_ms, 3),
        "client_host": client_host,
    }

    with LOG_LOCK:
        file_exists = API_USAGE_LOG_PATH.exists()

        with API_USAGE_LOG_PATH.open("a", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=API_LOG_COLUMNS)

            if not file_exists:
                writer.writeheader()

            writer.writerow(row)


def read_api_usage_log() -> pd.DataFrame:
    if not API_USAGE_LOG_PATH.exists():
        return pd.DataFrame(columns=API_LOG_COLUMNS)

    return pd.read_csv(API_USAGE_LOG_PATH)


def build_metrics_payload() -> dict:
    dataframe = read_api_usage_log()

    if dataframe.empty:
        return {
            "total_requests": 0,
            "error_count": 0,
            "error_rate": 0,
            "average_response_time_ms": 0,
            "p95_response_time_ms": 0,
            "requests_by_path": {},
            "requests_by_status_code": {},
            "last_request_utc": None,
        }

    dataframe["status_code"] = dataframe["status_code"].astype(int)
    dataframe["response_time_ms"] = dataframe["response_time_ms"].astype(float)

    total_requests = int(len(dataframe))
    error_count = int((dataframe["status_code"] >= 400).sum())

    requests_by_path = (
        dataframe.groupby("path")
        .size()
        .sort_values(ascending=False)
        .to_dict()
    )

    requests_by_status_code = (
        dataframe.groupby("status_code")
        .size()
        .sort_index()
        .to_dict()
    )

    return {
        "total_requests": total_requests,
        "error_count": error_count,
        "error_rate": round(error_count / total_requests, 4),
        "average_response_time_ms": round(
            float(dataframe["response_time_ms"].mean()),
            3,
        ),
        "p95_response_time_ms": round(
            float(dataframe["response_time_ms"].quantile(0.95)),
            3,
        ),
        "requests_by_path": {
            str(key): int(value) for key, value in requests_by_path.items()
        },
        "requests_by_status_code": {
            str(key): int(value) for key, value in requests_by_status_code.items()
        },
        "last_request_utc": str(dataframe["timestamp_utc"].iloc[-1]),
    }


@app.middleware("http")
async def log_api_requests(request: Request, call_next):
    start_time = time.perf_counter()
    status_code = 500

    try:
        response = await call_next(request)
        status_code = response.status_code
        return response
    finally:
        response_time_ms = (time.perf_counter() - start_time) * 1000
        client_host = request.client.host if request.client else "unknown"

        append_api_log(
            method=request.method,
            path=request.url.path,
            status_code=status_code,
            response_time_ms=response_time_ms,
            client_host=client_host,
        )


@app.get("/")
def root() -> dict:
    return {
        "service": "Cyber Risk Intelligence API",
        "status": "running",
        "docs": "/docs",
        "metrics": "/metrics",
    }


@app.get("/health")
def health_check() -> dict:
    database_exists = ANALYTICS_DATABASE_PATH.exists()
    model_exists = MODEL_PATH.exists()
    monitoring_log_exists = API_USAGE_LOG_PATH.exists()

    return {
        "status": "ok" if database_exists else "missing_database",
        "analytics_database": str(ANALYTICS_DATABASE_PATH),
        "analytics_database_exists": database_exists,
        "model_path": str(MODEL_PATH),
        "model_exists": model_exists,
        "monitoring_log_path": str(API_USAGE_LOG_PATH),
        "monitoring_log_exists": monitoring_log_exists,
    }


@app.get("/metrics")
def get_api_metrics() -> dict:
    return build_metrics_payload()


@app.get("/vulnerabilities/top")
def get_top_vulnerabilities(
    limit: int = Query(default=20, ge=1, le=100),
    priority_level: Optional[str] = Query(default=None),
) -> list[dict]:
    query = """
        select
            cve_id,
            vendor,
            product_name,
            cwe_id,
            published_date,
            cvss_base_score,
            cvss_base_severity,
            epss_score,
            is_known_exploited,
            attack_vector,
            risk_score,
            priority_level
        from mart_vulnerability_priority
        where (? is null or priority_level = ?)
        order by risk_score desc, cvss_base_score desc
        limit ?
    """

    return run_query(query, [priority_level, priority_level, limit])


@app.get("/vulnerabilities/{cve_id}")
def get_vulnerability_by_cve(cve_id: str) -> dict:
    query = """
        select
            *
        from mart_vulnerability_priority
        where upper(cve_id) = upper(?)
        limit 1
    """

    results = run_query(query, [cve_id])

    if not results:
        raise HTTPException(
            status_code=404,
            detail=f"CVE not found: {cve_id}",
        )

    return results[0]


@app.get("/vendors/risk-summary")
def get_vendor_risk_summary(
    limit: int = Query(default=20, ge=1, le=100),
    has_known_exploited: Optional[bool] = Query(default=None),
) -> list[dict]:
    query = """
        select
            vendor,
            product_name,
            total_vulnerabilities,
            known_exploited_count,
            average_risk_score,
            maximum_risk_score,
            average_epss_score,
            critical_count,
            high_count,
            critical_or_high_count,
            vendor_exploitation_status
        from mart_vendor_risk_summary
        where (
            ? is null
            or (? = true and known_exploited_count > 0)
            or (? = false and known_exploited_count = 0)
        )
        order by known_exploited_count desc, maximum_risk_score desc
        limit ?
    """

    return run_query(
        query,
        [has_known_exploited, has_known_exploited, has_known_exploited, limit],
    )


@app.get("/cwe/risk-summary")
def get_cwe_risk_summary(
    limit: int = Query(default=20, ge=1, le=100),
) -> list[dict]:
    query = """
        select
            cwe_id,
            total_vulnerabilities,
            known_exploited_count,
            average_risk_score,
            maximum_risk_score,
            average_cvss_score,
            average_epss_score,
            cwe_exploitation_status
        from mart_cwe_risk_summary
        order by known_exploited_count desc, maximum_risk_score desc
        limit ?
    """

    return run_query(query, [limit])


@app.get("/trends/monthly")
def get_monthly_trends() -> list[dict]:
    query = """
        select
            published_year,
            published_month,
            month_label,
            total_cve_count,
            known_exploited_count,
            average_cvss_score,
            average_epss_score,
            critical_count,
            high_count,
            critical_or_high_count,
            network_attack_vector_count
        from mart_monthly_vulnerability_trends
        order by published_year, published_month
    """

    return run_query(query)


@app.post("/predict-priority")
def predict_priority(request: PriorityPredictionRequest) -> dict:
    model = load_model()

    input_dataframe = pd.DataFrame(
        [
            {
                "cvss_base_score": request.cvss_base_score,
                "epss_score": request.epss_score or 0,
                "epss_percentile": request.epss_percentile or 0,
                "is_known_exploited": request.is_known_exploited,
                "reference_count": request.reference_count,
                "affected_entry_count": request.affected_entry_count,
                "published_month": request.published_month,
                "cvss_base_severity": request.cvss_base_severity,
                "attack_vector": request.attack_vector,
                "attack_complexity": request.attack_complexity,
                "privileges_required": request.privileges_required,
                "user_interaction": request.user_interaction,
                "cwe_id": request.cwe_id,
            }
        ]
    )

    prediction = model.predict(input_dataframe)[0]

    response = {
        "predicted_priority_level": str(prediction),
        "input": request.model_dump(),
    }

    if hasattr(model, "predict_proba"):
        probabilities = model.predict_proba(input_dataframe)[0]
        classes = model.classes_

        response["prediction_probabilities"] = {
            str(class_name): round(float(probability), 4)
            for class_name, probability in zip(classes, probabilities)
        }

    return response


@app.get("/remediation/{cve_id}")
def get_remediation_plan(cve_id: str) -> dict:
    plan = generate_remediation_plan(cve_id)

    if not plan.get("found"):
        raise HTTPException(
            status_code=404,
            detail=f"CVE not found in analytics mart: {cve_id}",
        )

    return plan