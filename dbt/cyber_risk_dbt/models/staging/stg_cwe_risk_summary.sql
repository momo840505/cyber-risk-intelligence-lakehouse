select
    cast(cwe_id as varchar) as cwe_id,
    cast(total_vulnerabilities as integer) as total_vulnerabilities,
    cast(known_exploited_count as integer) as known_exploited_count,
    cast(average_risk_score as double) as average_risk_score,
    cast(maximum_risk_score as double) as maximum_risk_score,
    cast(average_cvss_score as double) as average_cvss_score,
    cast(average_epss_score as double) as average_epss_score
from {{ source('gold', 'raw_cwe_risk_summary') }}
