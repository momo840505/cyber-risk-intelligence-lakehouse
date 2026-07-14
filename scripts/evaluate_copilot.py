from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from rag.remediation_copilot import generate_remediation_plan


REPORTS_DIR = BASE_DIR / "reports"

EVAL_REPORT_PATH = REPORTS_DIR / "copilot_eval_report.csv"
EVAL_SUMMARY_PATH = REPORTS_DIR / "copilot_eval_summary.json"


EVAL_CVES = [
    "CVE-2026-48908",
    "CVE-2026-48282",
    "CVE-2026-48939",
    "CVE-2026-56290",
    "CVE-2016-20068",
]


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
        "passed": passed,
    }


def main() -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    rows = []

    for cve_id in EVAL_CVES:
        plan = generate_remediation_plan(cve_id)
        rows.append(evaluate_plan(plan))

    report_dataframe = pd.DataFrame(rows)
    report_dataframe.to_csv(EVAL_REPORT_PATH, index=False)

    summary = {
        "evaluated_cases": int(len(report_dataframe)),
        "passed_cases": int(report_dataframe["passed"].sum()),
        "failed_cases": int((~report_dataframe["passed"]).sum()),
        "pass_rate": round(float(report_dataframe["passed"].mean()), 4),
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
