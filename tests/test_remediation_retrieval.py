from rag.remediation_engine import RetrievedDocument, build_context_aware_actions


def test_retrieved_document_contributes_actions() -> None:
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
