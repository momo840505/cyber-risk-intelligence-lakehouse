# CWE Remediation Guidance

Common Weakness Enumeration categories help explain the weakness type behind a CVE.

CWE-434 Unrestricted Upload of File with Dangerous Type:
- Restrict allowed file types.
- Validate file extension and MIME type.
- Store uploaded files outside the web root.
- Rename uploaded files using safe generated names.
- Scan uploaded files before processing.
- Prevent execution permission on upload directories.

CWE-22 Path Traversal:
- Normalise and validate file paths.
- Reject path traversal sequences such as ../.
- Use allowlisted directories.
- Avoid directly using user-controlled input in file paths.
- Enforce least privilege for file access.

CWE-89 SQL Injection:
- Use parameterised queries.
- Avoid string concatenation in SQL statements.
- Validate and constrain user input.
- Use least-privilege database accounts.
- Monitor suspicious query patterns.

CWE-79 Cross-Site Scripting:
- Apply output encoding.
- Sanitise user-generated content.
- Use Content Security Policy.
- Avoid unsafe HTML rendering.
- Validate input where appropriate.
