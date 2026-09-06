from __future__ import annotations

import json
import sys
from pathlib import Path

import duckdb
import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from rag.remediation_copilot import CWE_ACTIONS, generate_remediation_plan


REPORTS_DIR = BASE_DIR / "reports"
ANALYTICS_DATABASE_PATH = BASE_DIR / "analytics" / "cyber_risk.duckdb"

EVAL_REPORT_PATH = REPORTS_DIR / "copilot_eval_report.csv"
EVAL_SUMMARY_PATH = REPORTS_DIR / "copilot_eval_summary.json"

EVAL_CASE_COUNT = 5


def select_eval_cves(limit: int = EVAL_CASE_COUNT) -> list[str]:
    """
    Pick CVE IDs to evaluate the copilot against, straight from the current
    analytics database instead of a hardcoded list.

    A hardcoded list breaks silently: NVD ingestion only pulls a rolling
    30-day window (see README 'Limitations'), so any specific CVE ID picked
    today can simply fall out of the dataset on a later pipeline run --
    every case then evaluates to found=False, which looks like the copilot
    is broken when actually the fixture CVE IDs are just stale. Selecting
    known-exploited CVEs by risk_score at evaluation time keeps this script
    correct across ingestion runs with no manual upkeep.
    """
    if not ANALYTICS_DATABASE_PATH.exists():
        raise FileNotFoundError(
            f"Analytics database not found: {ANALYTICS_DATABASE_PATH}. "
            "Run scripts/run_dbt.py (or scripts/run_pipeline.py) first."
        )

    query = """
        select cve_id
        from mart_vulnerability_priority
        order by is_known_exploited desc, risk_score desc
        limit ?
    """

    with duckdb.connect(str(ANALYTICS_DATABASE_PATH), read_only=True) as connection:
        dataframe = connection.execute(query, [limit]).fetchdf()

    if dataframe.empty:
        raise RuntimeError(
            "mart_vulnerability_priority is empty -- run the full pipeline "
            "(scripts/run_pipeline.py) before evaluating the copilot."
        )

    return dataframe["cve_id"].tolist()


def evaluate_plan(plan: dict) -> dict:
    found = bool(plan.get("found"))
    has_actions = bool(plan.get("recommended_actions"))
    has_sources = bool(plan.get("retrieved_sources"))
    has_safety_note = bool(plan.get("safety_note"))
    has_priority_reason = bool(plan.get("why_this_priority"))

    passed = all(
        [
            found,
            has_actions,
            has_sources,
            has_safety_note,
            has_priority_reason,
        ]
    )

    # Transparency signal, not part of "passed": `passed` above is a
    # pipeline-completeness check (see README "Copilot Evaluation" section
    # for why it will be ~100% by construction regardless of CVE). This
    # field instead checks whether the plan's actions actually include any
    # of the weakness-specific guidance from CWE_ACTIONS for this CVE's own
    # CWE, i.e. content beyond the fixed urgency-tier baseline actions that
    # get appended for every CVE.
    cwe_id = str((plan.get("vulnerability_context") or {}).get("cwe_id"))
    cwe_specific_options = CWE_ACTIONS.get(cwe_id, [])
    has_cwe_mapping = bool(cwe_specific_options)
    recommended_actions = plan.get("recommended_actions", []) or []
    has_cwe_specific_guidance = has_cwe_mapping and any(
        action in recommended_actions for action in cwe_specific_options
    )

    return {
        "cve_id": plan.get("cve_id"),
        "found": found,
        "urgency": plan.get("urgency"),
        "priority_level": plan.get("priority_level"),
        "recommended_sla": plan.get("recommended_sla"),
        "action_count": len(plan.get("recommended_actions", [])),
        "source_count": len(plan.get("retrieved_sources", [])),
        "has_safety_note": has_safety_note,
        "has_priority_reason": has_priority_reason,
        "cwe_id": cwe_id,
        "has_cwe_mapping": has_cwe_mapping,
        "has_cwe_specific_guidance": has_cwe_specific_guidance,
        "passed": passed,
    }


def main() -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    eval_cves = select_eval_cves()

    rows = []

    for cve_id in eval_cves:
        plan = generate_remediation_plan(cve_id)
        rows.append(evaluate_plan(plan))

    report_dataframe = pd.DataFrame(rows)
    report_dataframe.to_csv(EVAL_REPORT_PATH, index=False)

    cases_with_cwe_mapping = int(report_dataframe["has_cwe_mapping"].sum())
    cwe_specific_guidance_rate = (
        round(
            float(
                report_dataframe.loc[
                    report_dataframe["has_cwe_mapping"], "has_cwe_specific_guidance"
                ].mean()
            ),
            4,
        )
        if cases_with_cwe_mapping > 0
        else None
    )

    summary = {
        "evaluated_cases": int(len(report_dataframe)),
        "passed_cases": int(report_dataframe["passed"].sum()),
        "failed_cases": int((~report_dataframe["passed"]).sum()),
        "pass_rate": round(float(report_dataframe["passed"].mean()), 4),
        "cases_with_cwe_mapping": cases_with_cwe_mapping,
        "cwe_specific_guidance_rate": cwe_specific_guidance_rate,
    }

    EVAL_SUMMARY_PATH.write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )

    print("\n========== Copilot Evaluation Report ==========")
    print(report_dataframe.to_string(index=False))
    print("\nSummary:")
    print(json.dumps(summary, indent=2))
    print(f"\nSaved report: {EVAL_REPORT_PATH}")
    print(f"Saved summary: {EVAL_SUMMARY_PATH}")


if __name__ == "__main__":
    main()
