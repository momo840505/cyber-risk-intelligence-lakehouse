# CVSS-Based Vulnerability Prioritisation

CVSS base score helps estimate the technical severity of a vulnerability.

General severity bands:
- Critical: 9.0 to 10.0
- High: 7.0 to 8.9
- Medium: 4.0 to 6.9
- Low: 0.1 to 3.9

Recommended actions:
- Critical vulnerabilities should be reviewed immediately.
- High vulnerabilities should be remediated in the next patch cycle or sooner.
- Medium vulnerabilities should be scheduled based on exposure and asset criticality.
- Low vulnerabilities should be tracked and remediated when practical.

Risk should not be based on CVSS alone.
Additional factors:
- Known exploitation
- Network exposure
- User interaction
- Privileges required
- Asset criticality
- Availability of compensating controls
