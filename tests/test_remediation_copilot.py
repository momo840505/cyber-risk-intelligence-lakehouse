"""
Unit tests for the pure decision-logic in rag/remediation_copilot.py.

This project previously had no automated test suite at all -- CI only
ran `python -m compileall`, which catches syntax errors but nothing
about behaviour. These tests cover the parts of the remediation copilot
that are pure functions (no database, no network, no LLM call), which
is exactly the code most worth unit-testing: it is deterministic,
fast, and a regression here would silently give operators the wrong
urgency/SLA for a real vulnerability.
"""

from __future__ import annotations

import pytest

from rag.remediation_copilot import (
    append_unique,
    build_context_aware_actions,
    build_retrieval_query,
    build_safe_fallback_query,
    classify_response_urgency,
    load_knowledge_base,
    recommend_sla,
    retrieve_documents,
)


# ---------------------------------------------------------------------------
# classify_response_urgency
# ---------------------------------------------------------------------------


def test_known_exploited_is_always_emergency() -> None:
    """A KEV-listed CVE is Emergency regardless of CVSS severity."""
    vulnerability = {
        "is_known_exploited": 1,
        "cvss_base_severity": "LOW",
        "priority_level": "Low",
    }
    assert classify_response_urgency(vulnerability) == "Emergency"


def test_critical_severity_without_kev_is_emergency() -> None:
    vulnerability = {
        "is_known_exploited": 0,
        "cvss_base_severity": "CRITICAL",
        "priority_level": "High",
    }
    assert classify_response_urgency(vulnerability) == "Emergency"


@pytest.mark.parametrize(
    ("priority_level", "expected_urgency"),
    [
        ("High", "High"),
        ("Medium", "Medium"),
        ("Low", "Low"),
    ],
)
def test_priority_level_maps_to_urgency_when_not_critical_or_exploited(
    priority_level: str,
    expected_urgency: str,
) -> None:
    vulnerability = {
        "is_known_exploited": 0,
        "cvss_base_severity": "MEDIUM",
        "priority_level": priority_level,
    }
    assert classify_response_urgency(vulnerability) == expected_urgency


def test_unknown_priority_level_defaults_to_low() -> None:
    vulnerability = {
        "is_known_exploited": 0,
        "cvss_base_severity": "LOW",
        "priority_level": "SomethingUnexpected",
    }
    assert classify_response_urgency(vulnerability) == "Low"


# ---------------------------------------------------------------------------
# recommend_sla
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("urgency", "expected_sla"),
    [
        ("Emergency", "24 to 72 hours"),
        ("High", "7 to 14 days"),
        ("Medium", "30 to 60 days"),
        ("Low", "Next planned maintenance window"),
    ],
)
def test_recommend_sla_matches_documented_windows(
    urgency: str,
    expected_sla: str,
) -> None:
    assert recommend_sla(urgency) == expected_sla


def test_recommend_sla_falls_back_for_unknown_urgency() -> None:
    assert recommend_sla("Unrecognised") == "Review manually"


# ---------------------------------------------------------------------------
# append_unique
# ---------------------------------------------------------------------------


def test_append_unique_deduplicates_actions() -> None:
    actions: list[str] = []
    append_unique(actions, "Apply vendor patch.")
    append_unique(actions, "Apply vendor patch.")
    append_unique(actions, "Isolate affected systems.")

    assert actions == ["Apply vendor patch.", "Isolate affected systems."]


def test_append_unique_ignores_empty_action() -> None:
    actions: list[str] = []
    append_unique(actions, "")
    assert actions == []


# ---------------------------------------------------------------------------
# build_context_aware_actions
# ---------------------------------------------------------------------------


def test_emergency_actions_include_isolation_guidance() -> None:
    vulnerability = {
        "is_known_exploited": 1,
        "cvss_base_severity": "CRITICAL",
        "priority_level": "Critical",
        "cwe_id": "CWE-89",
        "attack_vector": "NETWORK",
    }

    actions = build_context_aware_actions(vulnerability, retrieved_documents=[])

    assert any("isolate" in action.lower() for action in actions)
    assert any(
        "parameteris" in action.lower() or "parameteriz" in action.lower()
        for action in actions
    ), "CWE-89 (SQL injection) actions should mention parameterised queries"
    assert len(actions) <= 10


def test_low_priority_actions_do_not_recommend_immediate_isolation() -> None:
    vulnerability = {
        "is_known_exploited": 0,
        "cvss_base_severity": "LOW",
        "priority_level": "Low",
        "cwe_id": None,
        "attack_vector": "LOCAL",
    }

    actions = build_context_aware_actions(vulnerability, retrieved_documents=[])

    assert not any("isolate" in action.lower() for action in actions)


# ---------------------------------------------------------------------------
# build_retrieval_query / build_safe_fallback_query
# ---------------------------------------------------------------------------


def test_retrieval_query_includes_cwe_specific_terms_for_sql_injection() -> None:
    vulnerability = {
        "cwe_id": "CWE-89",
        "cvss_base_severity": "HIGH",
        "priority_level": "High",
        "attack_vector": "NETWORK",
        "is_known_exploited": 0,
    }

    query = build_retrieval_query(vulnerability)

    assert "sql injection" in query.lower()
    assert "CWE-89" in query


def test_safe_fallback_query_never_raises_on_missing_fields() -> None:
    # build_safe_fallback_query must degrade gracefully when a vulnerability
    # record is missing optional fields (e.g. cwe_id is NULL in the mart).
    query = build_safe_fallback_query({})
    assert isinstance(query, str)
    assert "remediation" in query.lower()


# ---------------------------------------------------------------------------
# retrieve_documents / load_knowledge_base (real I/O against the actual
# markdown knowledge base shipped in the repo -- deliberately not mocked,
# so this also catches an accidentally-deleted or renamed knowledge file)
# ---------------------------------------------------------------------------


def test_knowledge_base_loads_without_error() -> None:
    documents = load_knowledge_base()
    assert len(documents) >= 1
    assert all("content" in document and document["content"] for document in documents)


def test_retrieve_documents_returns_ranked_results_for_sql_injection_query() -> None:
    results = retrieve_documents("sql injection parameterised queries", top_k=3)

    assert 1 <= len(results) <= 3
    # Results must be sorted by descending similarity score.
    scores = [document.score for document in results]
    assert scores == sorted(scores, reverse=True)
