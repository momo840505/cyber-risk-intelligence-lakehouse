select
    cast(vendor as varchar) as vendor,
    cast(product_name as varchar) as product_name,
    cast(total_vulnerabilities as integer) as total_vulnerabilities,
    cast(known_exploited_count as integer) as known_exploited_count,
    cast(average_risk_score as double) as average_risk_score,
    cast(maximum_risk_score as double) as maximum_risk_score,
    cast(average_epss_score as double) as average_epss_score,
    cast(critical_count as integer) as critical_count,
    cast(high_count as integer) as high_count
from {{ source('gold', 'raw_vendor_risk_summary') }}
