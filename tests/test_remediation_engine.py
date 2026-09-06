from __future__ import annotations

import pytest

from rag.remediation_engine import (
    RetrievedDocument,
    append_unique,
    build_context_aware_actions,
    build_retrieval_query,
    classify_response_urgency,
    extract_retrieved_actions,
    load_knowledge_base,
    recommend_sla,
    retrieve_documents,
)


def test_known_exploited_is_emergency() -> None:
    vulnerability = {
        "is_known_exploited": 1,
        "cvss_base_severity": "LOW",
        "priority_level": "Low",
    }
    assert classify_response_urgency(vulnerability) == "Emergency"


def test_critical_is_emergency() -> None:
    vulnerability = {
        "is_known_exploited": 0,
        "cvss_base_severity": "CRITICAL",
        "priority_level": "High",
    }
    assert classify_response_urgency(vulnerability) == "Emergency"


@pytest.mark.parametrize(
    ("priority", "expected"),
    [("High", "High"), ("Medium", "Medium"), ("Low", "Low")],
)
def test_priority_maps_to_urgency(priority: str, expected: str) -> None:
    vulnerability = {
        "is_known_exploited": 0,
        "cvss_base_severity": "MEDIUM",
        "priority_level": priority,
    }
    assert classify_response_urgency(vulnerability) == expected


@pytest.mark.parametrize(
    ("urgency", "expected"),
    [
        ("Emergency", "24 to 72 hours"),
        ("High", "7 to 14 days"),
        ("Medium", "30 to 60 days"),
        ("Low", "Next planned maintenance window"),
    ],
)
def test_sla_mapping(urgency: str, expected: str) -> None:
    assert recommend_sla(urgency) == expected


def test_append_unique_deduplicates() -> None:
    actions: list[str] = []
    append_unique(actions, "Patch.")
    append_unique(actions, "Patch.")
    assert actions == ["Patch."]


def test_retrieved_action_is_extracted() -> None:
    document = RetrievedDocument(
        file_name="test.md",
        score=0.5,
        content="# Test\n\nRecommended actions:\n- Rotate exposed credentials\n",
    )
    assert extract_retrieved_actions(document) == ["Rotate exposed credentials."]


def test_retrieved_action_is_used() -> None:
    vulnerability = {
        "is_known_exploited": 0,
        "cvss_base_severity": "MEDIUM",
        "priority_level": "Medium",
        "attack_vector": "LOCAL",
        "cwe_id": "CWE-999",
    }
    document = RetrievedDocument(
        file_name="test.md",
        score=0.5,
        content="# Test\n\nRecommended actions:\n- Rotate exposed credentials\n",
    )
    actions = build_context_aware_actions(vulnerability, [document])
    assert "Rotate exposed credentials." in actions


def test_sql_injection_gets_parameterised_query_guidance() -> None:
    vulnerability = {
        "is_known_exploited": 0,
        "cvss_base_severity": "HIGH",
        "priority_level": "High",
        "attack_vector": "NETWORK",
        "cwe_id": "CWE-89",
    }
    actions = build_context_aware_actions(vulnerability, [])
    assert any("parameterised" in action.lower() for action in actions)


def test_retrieval_query_contains_context() -> None:
    vulnerability = {
        "cwe_id": "CWE-89",
        "cvss_base_severity": "HIGH",
        "priority_level": "High",
        "attack_vector": "NETWORK",
        "is_known_exploited": 0,
    }
    query = build_retrieval_query(vulnerability)
    assert "CWE-89" in query
    assert "NETWORK" in query


def test_knowledge_base_loads() -> None:
    documents = load_knowledge_base()
    assert documents
    assert all(document["content"] for document in documents)


def test_retrieval_is_ranked() -> None:
    results = retrieve_documents("sql injection parameterised query", top_k=3)
    scores = [result.score for result in results]
    assert scores == sorted(scores, reverse=True)
