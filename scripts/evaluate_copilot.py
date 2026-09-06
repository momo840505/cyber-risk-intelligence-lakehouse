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

# A retrieved knowledge-base doc with a cosine similarity below this is
# functionally noise -- TF-IDF cosine similarity near 0 means almost no
# vocabulary overlap with the query, i.e. the retrieval step found nothing
# meaningfully related to this CVE.
MIN_RELEVANT_SIMILARITY = 0.05

# Situations where the RAG filtering logic (see
# rag/remediation_copilot.py::filter_documents_for_context) is SUPPOSED to
# pull in a specific document. Used to check the retrieval behaved
# correctly for this case, not just that it returned *something*.
CONTEXT_SPECIFIC_SOURCES = {
    "known_exploited": "cisa_kev_remediation.md",
    "emergency": "emergency_response.md",
}


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

    # ------------------------------------------------------------------
    # Quality signals, not just completeness: `passed` above only checks
    # that fields are non-empty (see README "Copilot Evaluation" section
    # for why that's ~100% by construction regardless of CVE). Everything
    # below instead checks whether the plan's CONTENT actually reflects
    # this specific CVE, using signals we can compute from real system
    # behaviour rather than a hand-graded "gold" answer:
    #
    #   - has_cwe_specific_guidance: did the actions include anything
    #     beyond the fixed urgency-tier baseline (only possible for the
    #     4 CWEs in CWE_ACTIONS -- honestly N/A otherwise, not a fail)
    #   - has_relevant_retrieval: did the RAG step actually find a
    #     knowledge-base doc with real vocabulary overlap, or just
    #     return its highest-scoring doc regardless of relevance
    #   - has_context_appropriate_source: for known-exploited /
    #     Emergency-urgency CVEs, did retrieval actually surface the
    #     specific doc that filter_documents_for_context is designed to
    #     prioritise for that situation
    # ------------------------------------------------------------------
    vulnerability_context = plan.get("vulnerability_context") or {}
    cwe_id = str(vulnerability_context.get("cwe_id"))
    urgency = plan.get("urgency")
    is_known_exploited = vulnerability_context.get("is_known_exploited") == 1

    cwe_specific_options = CWE_ACTIONS.get(cwe_id, [])
    has_cwe_mapping = bool(cwe_specific_options)
    recommended_actions = plan.get("recommended_actions", []) or []
    has_cwe_specific_guidance = has_cwe_mapping and any(
        action in recommended_actions for action in cwe_specific_options
    )

    retrieved_sources = plan.get("retrieved_sources", []) or []
    retrieved_file_names = {source.get("file_name") for source in retrieved_sources}
    top_retrieval_similarity = max(
        (source.get("similarity_score", 0.0) for source in retrieved_sources),
        default=0.0,
    )
    has_relevant_retrieval = top_retrieval_similarity >= MIN_RELEVANT_SIMILARITY

    expected_context_sources = []
    if is_known_exploited:
        expected_context_sources.append(CONTEXT_SPECIFIC_SOURCES["known_exploited"])
    if urgency == "Emergency":
        expected_context_sources.append(CONTEXT_SPECIFIC_SOURCES["emergency"])

    has_context_appropriate_source = not expected_context_sources or any(
        file_name in retrieved_file_names for file_name in expected_context_sources
    )

    # quality_score averages only the checks that actually apply to this
    # case (has_cwe_specific_guidance is meaningless -- not failing -- when
    # this CWE has no mapping at all), so a case with no CWE mapping isn't
    # unfairly punished for a gap the copilot has no way to fill.
    quality_checks = [has_relevant_retrieval, has_context_appropriate_source]
    if has_cwe_mapping:
        quality_checks.append(has_cwe_specific_guidance)
    quality_score = round(sum(quality_checks) / len(quality_checks), 4)

    return {
        "cve_id": plan.get("cve_id"),
        "found": found,
        "urgency": urgency,
        "priority_level": plan.get("priority_level"),
        "recommended_sla": plan.get("recommended_sla"),
        "action_count": len(recommended_actions),
        "source_count": len(retrieved_sources),
        "has_safety_note": has_safety_note,
        "has_priority_reason": has_priority_reason,
        "cwe_id": cwe_id,
        "has_cwe_mapping": has_cwe_mapping,
        "has_cwe_specific_guidance": has_cwe_specific_guidance,
        "top_retrieval_similarity": round(top_retrieval_similarity, 4),
        "has_relevant_retrieval": has_relevant_retrieval,
        "has_context_appropriate_source": has_context_appropriate_source,
        "quality_score": quality_score,
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
        "pass_rate_note": (
            "Completeness check only (found + non-empty fields) -- see "
            "mean_quality_score below for whether the content is actually "
            "specific to each CVE."
        ),
        "cases_with_cwe_mapping": cases_with_cwe_mapping,
        "cwe_specific_guidance_rate": cwe_specific_guidance_rate,
        "cases_with_relevant_retrieval": int(
            report_dataframe["has_relevant_retrieval"].sum()
        ),
        "cases_with_context_appropriate_source": int(
            report_dataframe["has_context_appropriate_source"].sum()
        ),
        "mean_quality_score": round(
            float(report_dataframe["quality_score"].mean()), 4
        ),
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
