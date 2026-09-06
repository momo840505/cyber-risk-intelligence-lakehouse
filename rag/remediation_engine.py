from __future__ import annotations

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
MAX_RETRIEVED_ACTIONS = 3
MAX_RECOMMENDED_ACTIONS = 15


@dataclass
class RetrievedDocument:
    file_name: str
    score: float
    content: str


CWE_ACTIONS = {
    "CWE-20": [
        "Validate input against an allowlist of expected types, lengths, ranges, and formats.",
        "Reject malformed input before it reaches security-sensitive processing.",
    ],
    "CWE-22": [
        "Normalise and validate file paths.",
        "Reject path traversal patterns such as ../.",
        "Use allowlisted directories.",
        "Enforce least-privilege file access.",
    ],
    "CWE-73": [
        "Do not allow untrusted input to directly control file names or paths.",
        "Map user-controlled identifiers to server-side allowlisted paths.",
    ],
    "CWE-78": [
        "Avoid invoking operating-system commands with untrusted input.",
        "Use structured process APIs and allowlisted arguments instead of shell command construction.",
        "Run the affected service with the minimum operating-system privileges required.",
    ],
    "CWE-79": [
        "Apply output encoding.",
        "Sanitise user-generated content.",
        "Use Content Security Policy.",
        "Avoid unsafe HTML rendering.",
    ],
    "CWE-89": [
        "Use parameterised queries or prepared statements.",
        "Remove string concatenation from SQL query construction.",
        "Validate and constrain user input.",
        "Use least-privilege database accounts.",
    ],
    "CWE-94": [
        "Remove or restrict dynamic code evaluation of untrusted input.",
        "Allow only trusted code, templates, or modules to be executed or loaded.",
        "Isolate code-execution components with least privilege and appropriate sandboxing controls.",
    ],
    "CWE-120": [
        "Use bounds-checked memory operations and validate buffer lengths before copying data.",
        "Apply vendor patches and enable available compiler and runtime memory protections.",
    ],
    "CWE-288": [
        "Enforce the same authentication controls across every alternate path and interface.",
        "Test direct and alternate access paths for authentication bypass.",
    ],
    "CWE-306": [
        "Require authentication before every security-sensitive function.",
        "Centralise authentication enforcement so alternate routes cannot bypass the control.",
    ],
    "CWE-352": [
        "Use anti-CSRF tokens for state-changing requests.",
        "Validate request origin or same-site protections where appropriate.",
    ],
    "CWE-416": [
        "Apply the vendor fix for the use-after-free condition.",
        "Use memory-safety tooling and runtime protections to detect invalid lifetime access during testing.",
    ],
    "CWE-434": [
        "Restrict allowed upload file types.",
        "Validate both file extension and MIME type.",
        "Store uploaded files outside the web root.",
        "Disable execution permissions on upload directories.",
    ],
    "CWE-601": [
        "Allowlist redirect destinations or use server-side identifiers for approved targets.",
        "Prefer relative redirects and reject untrusted external redirect URLs.",
    ],
    "CWE-787": [
        "Apply the vendor fix for the out-of-bounds write condition.",
        "Use bounds checking, memory-safe components, and available exploit mitigations where feasible.",
    ],
    "CWE-862": [
        "Enforce authorisation checks on every protected operation and resource.",
        "Use deny-by-default access control and test for direct-object access bypasses.",
    ],
}


def load_knowledge_base() -> list[dict]:
    documents = []
    for markdown_path in sorted(KNOWLEDGE_BASE_DIR.glob("*.md")):
        content = markdown_path.read_text(encoding="utf-8")
        documents.append({"file_name": markdown_path.name, "content": content})
    if not documents:
        raise FileNotFoundError(f"No knowledge base files found in {KNOWLEDGE_BASE_DIR}")
    return documents


def retrieve_documents(query: str, top_k: int = 5) -> list[RetrievedDocument]:
    documents = load_knowledge_base()
    corpus = [document["content"] for document in documents]
    vectorizer = TfidfVectorizer(stop_words="english")
    document_matrix = vectorizer.fit_transform(corpus)
    query_vector = vectorizer.transform([query])
    scores = cosine_similarity(query_vector, document_matrix).flatten()
    ranked_indexes = scores.argsort()[::-1][:top_k]
    return [
        RetrievedDocument(
            file_name=documents[index]["file_name"],
            score=float(scores[index]),
            content=documents[index]["content"],
        )
        for index in ranked_indexes
    ]


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
    return {
        "Emergency": "24 to 72 hours",
        "High": "7 to 14 days",
        "Medium": "30 to 60 days",
        "Low": "Next planned maintenance window",
    }.get(urgency, "Review manually")


def filter_documents_for_context(
    retrieved_documents: list[RetrievedDocument],
    vulnerability: dict,
) -> list[RetrievedDocument]:
    urgency = classify_response_urgency(vulnerability)
    is_known_exploited = vulnerability.get("is_known_exploited") == 1
    filtered = []
    for document in retrieved_documents:
        if document.file_name == "cisa_kev_remediation.md" and not is_known_exploited:
            continue
        if document.file_name == "emergency_response.md" and urgency != "Emergency":
            continue
        if document.score <= 0:
            continue
        filtered.append(document)
    return filtered[:3]


def get_vulnerability_context(cve_id: str) -> Optional[dict]:
    if not ANALYTICS_DATABASE_PATH.exists():
        raise FileNotFoundError(
            f"Analytics database not found: {ANALYTICS_DATABASE_PATH}. Run scripts/run_dbt.py first."
        )

    query = """
        select
            cve_id, vendor, product_name, cwe_id, published_date,
            cvss_base_score, cvss_base_severity, epss_score, epss_percentile,
            is_known_exploited, attack_vector, attack_complexity,
            privileges_required, user_interaction, reference_count,
            affected_entry_count, risk_score, priority_level,
            exploitation_status, is_network_exploitable, is_high_priority
        from mart_vulnerability_priority
        where upper(cve_id) = upper(?)
        limit 1
    """
    with duckdb.connect(str(ANALYTICS_DATABASE_PATH), read_only=True) as connection:
        dataframe = connection.execute(query, [cve_id]).fetchdf()
    if dataframe.empty:
        return None
    record = dataframe.iloc[0].to_dict()
    return {key: None if pd.isna(value) else value for key, value in record.items()}


def build_retrieval_query(vulnerability: dict) -> str:
    parts = [
        str(vulnerability.get("cwe_id") or ""),
        str(vulnerability.get("cvss_base_severity") or ""),
        str(vulnerability.get("priority_level") or ""),
        str(vulnerability.get("attack_vector") or ""),
        "vulnerability remediation patch mitigation validation",
    ]
    if vulnerability.get("is_known_exploited") == 1:
        parts.append("known exploited urgent remediation")
    if classify_response_urgency(vulnerability) == "Emergency":
        parts.append("emergency isolation monitoring")
    return " ".join(parts)


def extract_retrieved_actions(document: RetrievedDocument) -> list[str]:
    actions = []
    in_action_section = False
    for raw_line in document.content.splitlines():
        line = raw_line.strip()
        if line.lower().startswith(("recommended actions", "recommended workflow", "trigger conditions")):
            in_action_section = True
            continue
        if line.startswith("#"):
            in_action_section = False
            continue
        if in_action_section and line.startswith("-"):
            action = line.lstrip("-").strip()
            if action:
                actions.append(action.rstrip(".") + ".")
        if in_action_section and re.match(r"^\d+\.\s+", line):
            action = re.sub(r"^\d+\.\s+", "", line).strip()
            if action:
                actions.append(action.rstrip(".") + ".")
    return actions


def append_unique(actions: list[str], action: str) -> bool:
    if action and action not in actions:
        actions.append(action)
        return True
    return False


def collect_retrieved_actions(
    retrieved_documents: list[RetrievedDocument],
    limit: int = MAX_RETRIEVED_ACTIONS,
) -> list[str]:
    actions: list[str] = []
    for document in retrieved_documents:
        for action in extract_retrieved_actions(document):
            append_unique(actions, action)
            if len(actions) >= limit:
                return actions
    return actions


def build_context_aware_actions(
    vulnerability: dict,
    retrieved_documents: list[RetrievedDocument],
) -> list[str]:
    actions: list[str] = []
    urgency = classify_response_urgency(vulnerability)
    cwe_id = str(vulnerability.get("cwe_id") or "")

    append_unique(actions, "Confirm whether the affected vendor and product are present in the environment.")
    append_unique(actions, "Assign a remediation owner and record the target completion date.")

    if urgency == "Emergency":
        append_unique(actions, "Prioritise remediation immediately.")
        append_unique(actions, "Apply the vendor patch or documented mitigation as soon as possible.")
        append_unique(actions, "If patching is delayed, isolate the affected system or restrict its exposure.")
    elif urgency == "High":
        append_unique(actions, "Schedule remediation in the high-priority patch window.")
        append_unique(actions, "Apply the vendor patch or a validated mitigation.")
    elif urgency == "Medium":
        append_unique(actions, "Schedule remediation in the next approved patch cycle.")
    else:
        append_unique(actions, "Track the issue for the next planned maintenance window.")

    if vulnerability.get("attack_vector") == "NETWORK":
        append_unique(actions, "Review network exposure and remove unnecessary external access.")

    for action in CWE_ACTIONS.get(cwe_id, []):
        append_unique(actions, action)

    for action in collect_retrieved_actions(retrieved_documents):
        append_unique(actions, action)

    append_unique(actions, "Validate the fix with rescanning or control verification.")
    append_unique(actions, "Record remediation evidence for audit and follow-up.")
    return actions[:MAX_RECOMMENDED_ACTIONS]


def get_retrieved_actions_used(
    retrieved_documents: list[RetrievedDocument],
    recommended_actions: list[str],
) -> list[str]:
    candidates = collect_retrieved_actions(retrieved_documents)
    return [action for action in candidates if action in recommended_actions]


def generate_remediation_plan(cve_id: str) -> dict:
    vulnerability = get_vulnerability_context(cve_id)
    if vulnerability is None:
        return {
            "cve_id": cve_id,
            "found": False,
            "message": "CVE not found in the current analytics mart.",
        }

    retrieval_query = build_retrieval_query(vulnerability)
    retrieved_documents = filter_documents_for_context(
        retrieve_documents(retrieval_query, top_k=5),
        vulnerability,
    )
    urgency = classify_response_urgency(vulnerability)
    actions = build_context_aware_actions(vulnerability, retrieved_documents)
    retrieved_actions_used = get_retrieved_actions_used(retrieved_documents, actions)

    reasons = []
    if vulnerability.get("is_known_exploited") == 1:
        reasons.append("The CVE is present in the known-exploited signal.")
    if vulnerability.get("cvss_base_score") is not None:
        reasons.append(
            f"CVSS base score is {vulnerability['cvss_base_score']} ({vulnerability.get('cvss_base_severity')})."
        )
    if vulnerability.get("attack_vector") == "NETWORK":
        reasons.append("The attack vector is network-accessible.")
    if vulnerability.get("cwe_id"):
        reasons.append(f"The weakness category is {vulnerability['cwe_id']}.")

    return {
        "cve_id": cve_id,
        "found": True,
        "priority_level": vulnerability.get("priority_level"),
        "risk_score": vulnerability.get("risk_score"),
        "urgency": urgency,
        "recommended_sla": recommend_sla(urgency),
        "vulnerability_context": vulnerability,
        "why_this_priority": reasons,
        "recommended_actions": actions,
        "retrieved_sources": [
            {
                "file_name": document.file_name,
                "similarity_score": round(document.score, 4),
            }
            for document in retrieved_documents
        ],
        "retrieved_actions_used": retrieved_actions_used,
        "retrieved_action_count": len(retrieved_actions_used),
        "method": "Retrieval-assisted rules. Retrieved documents contribute actions; no generative model is used.",
    }


def format_plan_as_markdown(plan: dict) -> str:
    if not plan.get("found"):
        return f"# Remediation Plan\n\n{plan['message']}"

    lines = [
        f"# Remediation Plan for {plan['cve_id']}",
        "",
        f"Priority: {plan['priority_level']}",
        f"Risk score: {plan['risk_score']}",
        f"Urgency: {plan['urgency']}",
        f"Recommended SLA: {plan['recommended_sla']}",
        "",
        "## Why this priority",
    ]
    lines.extend(f"- {reason}" for reason in plan["why_this_priority"])
    lines.extend(["", "## Recommended actions"])
    lines.extend(f"- {action}" for action in plan["recommended_actions"])
    lines.extend(["", "## Retrieved sources"])
    lines.extend(
        f"- {source['file_name']} (similarity: {source['similarity_score']})"
        for source in plan["retrieved_sources"]
    )
    lines.extend(["", "## Method", f"- {plan['method']}"])
    return "\n".join(lines)


def main() -> None:
    cve_id = input("Enter CVE ID: ").strip()
    if not re.match(r"^CVE-\d{4}-\d+$", cve_id, flags=re.IGNORECASE):
        raise ValueError("Invalid CVE ID format. Example: CVE-2026-48908")
    print(format_plan_as_markdown(generate_remediation_plan(cve_id)))


if __name__ == "__main__":
    main()
