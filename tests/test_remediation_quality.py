from rag.remediation_engine import (
    CWE_ACTIONS,
    RetrievedDocument,
    build_context_aware_actions,
    get_retrieved_actions_used,
)
from scripts.evaluate_remediation import evaluate_cwe_action


def test_unmapped_cwe_is_not_counted_as_cwe_success() -> None:
    mapped, passed = evaluate_cwe_action("CWE-99999", ["Patch."])
    assert mapped is False
    assert passed is None


def test_mapped_cwe_requires_expected_action() -> None:
    mapped, passed = evaluate_cwe_action("CWE-89", ["Patch."])
    assert mapped is True
    assert passed is False


def test_common_code_injection_cwes_have_mappings() -> None:
    assert "CWE-78" in CWE_ACTIONS
    assert "CWE-94" in CWE_ACTIONS


def test_retrieval_contribution_is_observable() -> None:
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
    used = get_retrieved_actions_used([document], actions)
    assert used == ["Rotate exposed credentials."]
