from __future__ import annotations

from fastapi.testclient import TestClient

import api.main as api_main


client = TestClient(api_main.app)


def test_livez_is_process_only() -> None:
    response = client.get("/livez")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readyz_returns_503_when_dependencies_are_missing(monkeypatch) -> None:
    monkeypatch.setattr(api_main, "database_is_ready", lambda: False)
    monkeypatch.setattr(api_main, "model_is_ready", lambda: False)
    response = client.get("/readyz")
    assert response.status_code == 503


def test_readyz_returns_200_when_dependencies_are_ready(monkeypatch) -> None:
    monkeypatch.setattr(api_main, "database_is_ready", lambda: True)
    monkeypatch.setattr(api_main, "model_is_ready", lambda: True)
    response = client.get("/readyz")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_invalid_cve_format_is_rejected() -> None:
    response = client.get("/vulnerabilities/not-a-cve")
    assert response.status_code == 422


def test_score_kev_horizon_returns_ranking_score(monkeypatch) -> None:
    class FakeModel:
        classes_ = [0, 1]

        def predict_proba(self, dataframe):
            return [[0.2, 0.8]]

    monkeypatch.setattr(api_main, "load_model", lambda: FakeModel())
    monkeypatch.setattr(api_main, "load_model_metrics", lambda: {"label_horizon_days": 180})

    response = client.post(
        "/score-kev-horizon",
        json={
            "cvss_base_score": 9.8,
            "reference_count": 8,
            "affected_entry_count": 2,
            "published_month": 9,
            "cvss_base_severity": "CRITICAL",
            "attack_vector": "NETWORK",
            "attack_complexity": "LOW",
            "privileges_required": "NONE",
            "user_interaction": "NONE",
            "cwe_id": "CWE-78"
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["kev_horizon_score"] == 0.8
    assert payload["label_horizon_days"] == 180
    assert payload["score_semantics"] == "uncalibrated_ranking_score"
    assert "known_exploited_probability" not in payload
    assert "predicted_known_exploited" not in payload


def test_old_exploitation_probability_endpoint_is_removed() -> None:
    response = client.post(
        "/predict-exploitation-likelihood",
        json={"cvss_base_score": 9.8, "published_month": 9},
    )
    assert response.status_code == 404
