from __future__ import annotations

import json
import sys
from pathlib import Path

import duckdb
import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from rag.remediation_engine import CWE_ACTIONS, generate_remediation_plan


REPORTS_DIR = BASE_DIR / "reports"
DATABASE_PATH = BASE_DIR / "analytics" / "cyber_risk.duckdb"
REPORT_PATH = REPORTS_DIR / "remediation_eval_report.csv"
SUMMARY_PATH = REPORTS_DIR / "remediation_eval_summary.json"
MIN_RETRIEVAL_SIMILARITY = 0.10


CASE_QUERIES = [
    ("kev", "is_known_exploited = 1"),
    ("critical_not_kev", "is_known_exploited = 0 and cvss_base_severity = 'CRITICAL'"),
    ("high", "is_known_exploited = 0 and priority_level = 'High'"),
    ("medium", "is_known_exploited = 0 and priority_level = 'Medium'"),
    ("low", "is_known_exploited = 0 and priority_level = 'Low'"),
]


def select_cases(per_group: int = 5) -> list[tuple[str, str]]:
    if not DATABASE_PATH.exists():
        raise FileNotFoundError(f"Analytics database not found: {DATABASE_PATH}")

    selected: list[tuple[str, str]] = []
    with duckdb.connect(str(DATABASE_PATH), read_only=True) as connection:
        for group, condition in CASE_QUERIES:
            query = f"""
                select cve_id
                from mart_vulnerability_priority
                where {condition}
                order by md5(cve_id)
                limit ?
            """
            rows = connection.execute(query, [per_group]).fetchall()
            selected.extend((group, row[0]) for row in rows)
    return selected


def evaluate_cwe_action(cwe_id: str, actions: list[str]) -> tuple[bool, bool | None]:
    mapped_actions = CWE_ACTIONS.get(cwe_id)
    if not mapped_actions:
        return False, None
    return True, any(action in actions for action in mapped_actions)


def evaluate_case(group: str, cve_id: str) -> dict:
    plan = generate_remediation_plan(cve_id)
    context = plan.get("vulnerability_context") or {}
    sources = plan.get("retrieved_sources") or []
    actions = plan.get("recommended_actions") or []
    retrieved_actions_used = plan.get("retrieved_actions_used") or []
    cwe_id = str(context.get("cwe_id") or "")

    top_similarity = max((source.get("similarity_score", 0.0) for source in sources), default=0.0)
    cwe_mapping_available, has_cwe_action = evaluate_cwe_action(cwe_id, actions)
    has_retrieval_signal = bool(sources) and top_similarity >= MIN_RETRIEVAL_SIMILARITY
    retrieval_contributed = bool(retrieved_actions_used)
    complete = bool(plan.get("found") and actions and plan.get("why_this_priority"))
    cwe_check_passed = (not cwe_mapping_available) or bool(has_cwe_action)

    return {
        "group": group,
        "cve_id": cve_id,
        "urgency": plan.get("urgency"),
        "cwe_id": cwe_id,
        "cwe_mapping_available": cwe_mapping_available,
        "action_count": len(actions),
        "source_count": len(sources),
        "top_similarity": round(top_similarity, 4),
        "has_retrieval_signal": has_retrieval_signal,
        "retrieval_contributed": retrieval_contributed,
        "retrieved_action_count": len(retrieved_actions_used),
        "has_expected_cwe_action": has_cwe_action,
        "complete": complete,
        "passed": complete and has_retrieval_signal and retrieval_contributed and cwe_check_passed,
    }


def main() -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    cases = select_cases()
    if not cases:
        raise RuntimeError("No evaluation cases were available in the analytics mart.")

    dataframe = pd.DataFrame(evaluate_case(group, cve_id) for group, cve_id in cases)
    dataframe.to_csv(REPORT_PATH, index=False)

    mapped_rows = dataframe[dataframe["cwe_mapping_available"]]
    cwe_action_rate = (
        round(float(mapped_rows["has_expected_cwe_action"].astype(bool).mean()), 4)
        if not mapped_rows.empty
        else None
    )

    summary = {
        "evaluation_type": "deterministic consistency checks; not accuracy or human-judged relevance",
        "evaluated_cases": int(len(dataframe)),
        "groups": dataframe.groupby("group").size().to_dict(),
        "pass_rate": round(float(dataframe["passed"].mean()), 4),
        "retrieval_signal_rate": round(float(dataframe["has_retrieval_signal"].mean()), 4),
        "retrieval_contribution_rate": round(float(dataframe["retrieval_contributed"].mean()), 4),
        "mapped_cwe_cases": int(len(mapped_rows)),
        "cwe_action_rate_on_mapped_cases": cwe_action_rate,
        "minimum_similarity_threshold": MIN_RETRIEVAL_SIMILARITY,
    }
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(dataframe.to_string(index=False))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
