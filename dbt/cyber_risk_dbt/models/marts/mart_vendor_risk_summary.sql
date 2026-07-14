with vendor_risk as (

    select *
    from {{ ref('stg_vendor_risk_summary') }}

)

select
    vendor,
    product_name,
    total_vulnerabilities,
    known_exploited_count,
    average_risk_score,
    maximum_risk_score,
    average_epss_score,
    critical_count,
    high_count,

    critical_count + high_count as critical_or_high_count,

    case
        when known_exploited_count > 0 then 'Has Known Exploited CVEs'
        else 'No Known Exploited CVEs'
    end as vendor_exploitation_status

from vendor_risk
