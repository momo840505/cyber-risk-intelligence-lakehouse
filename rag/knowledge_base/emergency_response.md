# Emergency Vulnerability Response

Emergency response is required when a vulnerability has strong exploitation signals or severe business impact.

Trigger conditions:
- Known exploited vulnerability.
- Critical CVSS score.
- Network exploitable attack vector.
- Public exploit availability.
- Affected asset is internet-facing.
- Sensitive data exposure is possible.

Recommended emergency actions:
- Assign an incident owner.
- Identify all affected assets.
- Apply vendor patch or mitigation.
- Isolate exposed systems if patching is delayed.
- Enable enhanced logging and monitoring.
- Hunt for signs of exploitation.
- Communicate risk to stakeholders.
- Verify remediation with rescanning.
- Record lessons learned.

Avoid:
- Publishing exploit instructions.
- Sharing offensive payloads.
- Running unapproved exploit testing in production.
