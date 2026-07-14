select
    cwe_id,
    total_vulnerabilities,
    known_exploited_count,
    average_risk_score,
    maximum_risk_score,
    average_cvss_score,
    average_epss_score,

    case
        when known_exploited_count > 0 then 'Has Known Exploited CVEs'
        else 'No Known Exploited CVEs'
    end as cwe_exploitation_status

from {{ ref('stg_cwe_risk_summary') }}
