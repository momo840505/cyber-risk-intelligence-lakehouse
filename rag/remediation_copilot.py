from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import duckdb
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


BASE_DIR = Path(__file__).resolve().parents[1]
KNOWLEDGE_BASE_DIR = BASE_DIR / "rag" / "knowledge_base"
ANALYTICS_DATABASE_PATH = BASE_DIR / "analytics" / "cyber_risk.duckdb"


@dataclass
class RetrievedDocument:
    file_name: str
    score: float
    content: str


CWE_ACTIONS = {
    "CWE-434": [
        "Restrict allowed upload file types.",
        "Validate both file extension and MIME type.",
        "Store uploaded files outside the web root.",
        "Rename uploaded files using safe generated names.",
        "Disable execution permissions on upload directories.",
        "Scan uploaded files before processing.",
    ],
    "CWE-22": [
        "Normalise and validate file paths.",
        "Reject path traversal patterns such as ../.",
        "Use allowlisted directories.",
        "Avoid directly using user-controlled input in file paths.",
        "Enforce least-privilege file access.",
    ],
    "CWE-89": [
        "Use parameterised queries or prepared statements.",
        "Remove string concatenation from SQL query construction.",
        "Validate and constrain user input.",
        "Use least-privilege database accounts.",
        "Monitor suspicious database query patterns.",
    ],
    "CWE-79": [
        "Apply output encoding.",
        "Sanitise user-generated content.",
        "Use Content Security Policy.",
        "Avoid unsafe HTML rendering.",
        "Validate input where appropriate.",
    ],
}


def load_knowledge_base() -> list[dict]:
    documents = []

    for markdown_path in sorted(KNOWLEDGE_BASE_DIR.glob("*.md")):
        content = markdown_path.read_text(encoding="utf-8")
        documents.append(
            {
                "file_name": markdown_path.name,
                "content": content,
            }
        )

    if not documents:
        raise FileNotFoundError(
            f"No knowledge base files found in {KNOWLEDGE_BASE_DIR}"
        )

    return documents


def retrieve_documents(query: str, top_k: int = 5) -> list[RetrievedDocument]:
    documents = load_knowledge_base()
    corpus = [document["content"] for document in documents]

    vectorizer = TfidfVectorizer(stop_words="english")
    document_matrix = vectorizer.fit_transform(corpus)
    query_vector = vectorizer.transform([query])

    scores = cosine_similarity(query_vector, document_matrix).flatten()
    ranked_indexes = scores.argsort()[::-1][:top_k]

    retrieved_documents = []

    for index in ranked_indexes:
        retrieved_documents.append(
            RetrievedDocument(
                file_name=documents[index]["file_name"],
                score=float(scores[index]),
                content=documents[index]["content"],
            )
        )

    return retrieved_documents


def filter_documents_for_context(
    retrieved_documents: list[RetrievedDocument],
    vulnerability: dict,
) -> list[RetrievedDocument]:
    urgency = classify_response_urgency(vulnerability)
    is_known_exploited = vulnerability.get("is_known_exploited") == 1

    filtered_documents = []

    for document in retrieved_documents:
        if document.file_name == "cisa_kev_remediation.md" and not is_known_exploited:
            continue

        if document.file_name == "emergency_response.md" and urgency != "Emergency":
            continue

        filtered_documents.append(document)

    if filtered_documents:
        return filtered_documents[:3]

    fallback_query = build_safe_fallback_query(vulnerability)
    fallback_documents = retrieve_documents(fallback_query, top_k=5)

    fallback_filtered = []

    for document in fallback_documents:
        if document.file_name == "cisa_kev_remediation.md" and not is_known_exploited:
            continue

        if document.file_name == "emergency_response.md" and urgency != "Emergency":
            continue

        fallback_filtered.append(document)

    return fallback_filtered[:3]


def get_vulnerability_context(cve_id: str) -> Optional[dict]:
    if not ANALYTICS_DATABASE_PATH.exists():
        raise FileNotFoundError(
            f"Analytics database not found: {ANALYTICS_DATABASE_PATH}. "
            "Run scripts/run_dbt.py first."
        )

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
            epss_percentile,
            is_known_exploited,
            attack_vector,
            attack_complexity,
            privileges_required,
            user_interaction,
            reference_count,
            affected_entry_count,
            risk_score,
            priority_level,
            exploitation_status,
            is_network_exploitable,
            is_high_priority
        from mart_vulnerability_priority
        where upper(cve_id) = upper(?)
        limit 1
    """

    with duckdb.connect(str(ANALYTICS_DATABASE_PATH), read_only=True) as connection:
        dataframe = connection.execute(query, [cve_id]).fetchdf()

    if dataframe.empty:
        return None

    record = dataframe.iloc[0].to_dict()

    for key, value in record.items():
        if pd.isna(value):
            record[key] = None

    return record


def build_retrieval_query(vulnerability: dict) -> str:
    cwe_id = str(vulnerability.get("cwe_id") or "")
    severity = str(vulnerability.get("cvss_base_severity") or "")
    priority_level = str(vulnerability.get("priority_level") or "")
    attack_vector = str(vulnerability.get("attack_vector") or "")

    query_parts = [
        cwe_id,
        severity,
        priority_level,
        attack_vector,
        "vulnerability remediation prioritisation patch validation",
    ]

    if cwe_id == "CWE-434":
        query_parts.append("unrestricted file upload dangerous file type remediation")
    elif cwe_id == "CWE-22":
        query_parts.append("path traversal file path validation remediation")
    elif cwe_id == "CWE-89":
        query_parts.append("sql injection parameterised queries remediation")
    elif cwe_id == "CWE-79":
        query_parts.append("cross site scripting output encoding remediation")

    if vulnerability.get("is_known_exploited") == 1:
        query_parts.append("CISA KEV known exploited urgent remediation")
    else:
        query_parts.append("standard vulnerability management scheduled remediation")

    if severity == "CRITICAL" or vulnerability.get("is_known_exploited") == 1:
        query_parts.append("emergency response isolation monitoring")
    else:
        query_parts.append("CVSS based prioritisation scheduled patching")

    return " ".join(query_parts)


def build_safe_fallback_query(vulnerability: dict) -> str:
    return (
        f"{vulnerability.get('cwe_id', '')} "
        f"{vulnerability.get('cvss_base_severity', '')} "
        "CWE remediation CVSS prioritisation vulnerability management"
    )


def classify_response_urgency(vulnerability: dict) -> str:
    if vulnerability.get("is_known_exploited") == 1:
        return "Emergency"
    if vulnerability.get("cvss_base_severity") == "CRITICAL":
        return "Emergency"
    if vulnerability.get("priority_level") == "High":
        return "High"
    if vulnerability.get("priority_level") == "Medium":
        return "Medium"
    return "Low"


def recommend_sla(urgency: str) -> str:
    sla_mapping = {
        "Emergency": "24 to 72 hours",
        "High": "7 to 14 days",
        "Medium": "30 to 60 days",
        "Low": "Next planned maintenance window",
    }

    return sla_mapping.get(urgency, "Review manually")


def append_unique(actions: list[str], action: str) -> None:
    if action and action not in actions:
        actions.append(action)


def build_context_aware_actions(
    vulnerability: dict,
    retrieved_documents: list[RetrievedDocument],
) -> list[str]:
    actions: list[str] = []
    urgency = classify_response_urgency(vulnerability)
    cwe_id = vulnerability.get("cwe_id")

    append_unique(actions, "Confirm whether the affected vendor and product are present in the environment.")
    append_unique(actions, "Assign a remediation owner and document the remediation deadline.")

    if urgency == "Emergency":
        append_unique(actions, "Prioritise remediation immediately.")
        append_unique(actions, "Apply vendor patches or mitigations as soon as possible.")
        append_unique(actions, "If patching is delayed, isolate affected systems or restrict exposure.")
        append_unique(actions, "Increase monitoring for related indicators of compromise.")
        append_unique(actions, "Review access logs, authentication logs, and network activity.")
    elif urgency == "High":
        append_unique(actions, "Schedule remediation within the high-priority patch window.")
        append_unique(actions, "Apply vendor patches or validated mitigations.")
        append_unique(actions, "Review whether the affected asset is internet-facing or business-critical.")
    elif urgency == "Medium":
        append_unique(actions, "Schedule remediation within the medium-priority remediation window.")
        append_unique(actions, "Apply the vendor patch during the next approved patch cycle.")
        append_unique(actions, "Use exposure and asset criticality to decide whether escalation is needed.")
    else:
        append_unique(actions, "Track the vulnerability for remediation in a planned maintenance window.")

    if vulnerability.get("attack_vector") == "NETWORK":
        append_unique(actions, "Review network exposure and restrict unnecessary external access.")

    for cwe_action in CWE_ACTIONS.get(str(cwe_id), []):
        append_unique(actions, cwe_action)

    append_unique(actions, "Validate remediation with rescanning or control verification.")
    append_unique(actions, "Record remediation evidence for audit and reporting.")

    return actions[:10]


def generate_remediation_plan(cve_id: str) -> dict:
    vulnerability = get_vulnerability_context(cve_id)

    if vulnerability is None:
        return {
            "cve_id": cve_id,
            "found": False,
            "message": "CVE not found in the current analytics mart.",
        }

    retrieval_query = build_retrieval_query(vulnerability)
    raw_retrieved_documents = retrieve_documents(retrieval_query, top_k=5)
    retrieved_documents = filter_documents_for_context(
        raw_retrieved_documents,
        vulnerability,
    )

    urgency = classify_response_urgency(vulnerability)
    sla = recommend_sla(urgency)
    actions = build_context_aware_actions(vulnerability, retrieved_documents)

    explanation = []

    if vulnerability.get("is_known_exploited") == 1:
        explanation.append(
            "This CVE appears in the known exploited vulnerability signal, "
            "so it should be prioritised for urgent remediation."
        )

    if vulnerability.get("cvss_base_score") is not None:
        explanation.append(
            f"The CVSS base score is {vulnerability['cvss_base_score']}, "
            f"with severity {vulnerability.get('cvss_base_severity')}."
        )

    if vulnerability.get("attack_vector") == "NETWORK":
        explanation.append(
            "The attack vector is NETWORK, which increases exposure risk because "
            "the vulnerability may be exploitable remotely."
        )

    if vulnerability.get("cwe_id"):
        explanation.append(
            f"The weakness category is {vulnerability['cwe_id']}, so remediation "
            "should consider weakness-specific controls."
        )

    return {
        "cve_id": cve_id,
        "found": True,
        "priority_level": vulnerability.get("priority_level"),
        "risk_score": vulnerability.get("risk_score"),
        "urgency": urgency,
        "recommended_sla": sla,
        "vulnerability_context": vulnerability,
        "why_this_priority": explanation,
        "recommended_actions": actions,
        "retrieved_sources": [
            {
                "file_name": document.file_name,
                "similarity_score": round(document.score, 4),
            }
            for document in retrieved_documents
        ],
        "safety_note": (
            "This copilot provides defensive remediation guidance only. "
            "It does not provide exploit instructions or offensive payloads."
        ),
    }


def format_plan_as_markdown(plan: dict) -> str:
    if not plan.get("found"):
        return f"# Remediation Plan\n\n{plan['message']}"

    lines = [
        f"# Remediation Plan for {plan['cve_id']}",
        "",
        f"Priority Level: {plan['priority_level']}",
        f"Risk Score: {plan['risk_score']}",
        f"Urgency: {plan['urgency']}",
        f"Recommended SLA: {plan['recommended_sla']}",
        "",
        "## Why This Priority",
    ]

    for reason in plan["why_this_priority"]:
        lines.append(f"- {reason}")

    lines.extend(["", "## Recommended Actions"])

    for action in plan["recommended_actions"]:
        lines.append(f"- {action}")

    lines.extend(["", "## Retrieved Knowledge Sources"])

    for source in plan["retrieved_sources"]:
        lines.append(
            f"- {source['file_name']} "
            f"(similarity score: {source['similarity_score']})"
        )

    lines.extend(["", "## Safety Note", plan["safety_note"]])

    return "\n".join(lines)


def main() -> None:
    cve_id = input("Enter CVE ID: ").strip()

    if not re.match(r"^CVE-\d{4}-\d+$", cve_id, flags=re.IGNORECASE):
        raise ValueError("Invalid CVE ID format. Example: CVE-2026-48908")

    plan = generate_remediation_plan(cve_id)
    markdown_plan = format_plan_as_markdown(plan)

    print("\n" + markdown_plan)
    print("\nJSON output:")
    print(json.dumps(plan, indent=2, default=str))


if __name__ == "__main__":
    main()
