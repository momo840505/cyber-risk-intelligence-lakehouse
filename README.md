# 🛡️ Cyber Risk Intelligence Lakehouse

![Python](https://img.shields.io/badge/Python-3.11%2B-blue)
![PySpark](https://img.shields.io/badge/PySpark-ETL-orange)
![Lakehouse](https://img.shields.io/badge/Architecture-Bronze%20%7C%20Silver%20%7C%20Gold-green)
![Status](https://img.shields.io/badge/Status-ETL%20Pipeline%20Completed-success)

A local cyber risk intelligence lakehouse built with **Python** and **PySpark**.  
The project ingests public cybersecurity vulnerability data, cleans and standardises it into Silver tables, then builds Gold analytics tables for vulnerability prioritisation, vendor risk analysis, CWE weakness summaries, and monthly vulnerability trend monitoring.

---

## 📌 Project Summary

Security teams often need to decide which vulnerabilities should be patched first.  
However, raw vulnerability feeds are usually fragmented across different sources, such as CVE records, CVSS severity scores, EPSS exploit probability, and known exploited vulnerability lists.

This project solves that problem by building a structured lakehouse pipeline that combines multiple vulnerability intelligence sources into analytics-ready tables.

The pipeline follows a standard data engineering architecture:

```text
Bronze Layer  →  Silver Layer  →  Gold Layer
Raw data         Clean data       Analytics-ready risk intelligence
```

---

## 🎯 Objectives

The main goals of this project are to:

- Ingest cybersecurity vulnerability data from public sources.
- Store raw data locally in a Bronze layer.
- Clean and standardise data using PySpark.
- Build Silver tables for KEV, EPSS, and NVD vulnerability records.
- Join vulnerability data across sources.
- Create Gold tables for risk prioritisation and reporting.
- Provide a foundation for future dashboard, API, and machine learning extensions.

---

## 🧠 Why This Project Matters

Not all vulnerabilities have the same level of operational risk.

A vulnerability with a high CVSS score is severe, but it may not be actively exploited.  
A vulnerability with a high EPSS score is more likely to be exploited.  
A vulnerability listed in CISA KEV has already been observed in real-world exploitation.

This project combines these signals to help prioritise vulnerabilities more effectively.

---

## 🏗️ Lakehouse Architecture

```mermaid
flowchart TD
    A[Public Cybersecurity Data Sources] --> B[Bronze Layer]
    B --> C[Silver ETL with PySpark]
    C --> D[Silver KEV Table]
    C --> E[Silver EPSS Table]
    C --> F[Silver NVD Table]

    D --> G[Gold ETL with PySpark]
    E --> G
    F --> G

    G --> H[Vulnerability Priority Table]
    G --> I[Vendor Risk Summary]
    G --> J[Monthly Vulnerability Trends]
    G --> K[CWE Risk Summary]

    H --> L[Future Dashboard / API / ML]
    I --> L
    J --> L
    K --> L
```

---

## 🗂️ Data Sources

This project is designed around three main public cybersecurity intelligence sources:

### 1. CISA Known Exploited Vulnerabilities

Used to identify vulnerabilities that are known to have been exploited in the real world.

Main information includes:

- CVE ID
- Vendor / project
- Product
- Vulnerability name
- Date added
- Due date
- Required action
- Known ransomware campaign use

---

### 2. FIRST EPSS

Used to estimate the probability that a vulnerability may be exploited.

Main information includes:

- CVE ID
- EPSS score
- EPSS percentile
- EPSS date

---

### 3. NVD Recent CVE Data

Used to extract vulnerability metadata, CVSS severity, affected products, weakness category, and publication dates.

Main information includes:

- CVE ID
- Published date
- Last modified date
- Vulnerability description
- CWE ID
- Affected vendor
- Affected product
- CVSS score
- CVSS severity
- Attack vector
- Attack complexity
- User interaction
- Impact metrics

---

## 📁 Project Structure

```text
cyber-risk-intelligence-lakehouse/
│
├── scripts/
│   ├── inspect_lakehouse.py
│   └── run_ingestion.py
│
├── src/
│   └── cyber_risk/
│       ├── __init__.py
│       ├── config.py
│       │
│       ├── ingestion/
│       │   ├── __init__.py
│       │   ├── download_epss.py
│       │   ├── download_kev.py
│       │   ├── download_nvd_recent.py
│       │   └── http_client.py
│       │
│       ├── etl/
│       │   ├── __init__.py
│       │   ├── spark_session.py
│       │   ├── build_silver_tables.py
│       │   └── build_gold_tables.py
│       │
│       └── quality/
│           └── __init__.py
│
├── .gitignore
├── pyproject.toml
├── requirements.txt
└── README.md
```

---

## 🥉 Bronze Layer

The Bronze layer stores raw downloaded vulnerability data.

This layer is intentionally excluded from Git because it contains generated local data files.

Expected local folder:

```text
data/bronze/
```

Example raw datasets:

```text
data/bronze/kev/
data/bronze/epss/
data/bronze/nvd/
```

---

## 🥈 Silver Layer

The Silver layer contains cleaned and standardised vulnerability data.

Generated Silver tables:

```text
data/silver/silver_kev
data/silver/silver_epss
data/silver/silver_nvd
```

Validated Silver output:

```text
Silver KEV: 1,631 rows
Silver EPSS: 5,000 rows
Silver NVD: 7,580 rows
```

### Silver KEV Table

Purpose: clean and standardise known exploited vulnerability records.

Important fields:

```text
cve_id
vendor_project
product
vulnerability_name
date_added
due_date
known_ransomware_campaign_use
required_action
short_description
notes
cwe_list
date_added_year
date_added_month
```

### Silver EPSS Table

Purpose: clean and standardise exploit probability scores.

Important fields:

```text
cve_id
epss_score
epss_percentile
epss_date
epss_year
epss_month
```

### Silver NVD Table

Purpose: clean and standardise CVE metadata, CVSS severity, CWE category, and affected products.

Important fields:

```text
cve_id
source_identifier
published_datetime
last_modified_datetime
vulnerability_status
description
cwe_id
affected_vendor
affected_product
affected_entry_count
reference_count
cvss_version
cvss_base_score
cvss_base_severity
cvss_vector_string
attack_vector
attack_complexity
privileges_required
user_interaction
confidentiality_impact
integrity_impact
availability_impact
published_date
last_modified_date
published_year
published_month
```

---

## 🥇 Gold Layer

The Gold layer contains analytics-ready risk intelligence tables.

Generated Gold tables:

```text
data/gold/vulnerability_priority
data/gold/vendor_risk_summary
data/gold/monthly_vulnerability_trends
data/gold/cwe_risk_summary
```

Validated Gold output:

```text
Gold Vulnerability Priority: 7,580 rows
Gold Vendor Risk Summary: 2,738 rows
Gold Monthly Trends: 2 rows
Gold CWE Risk Summary: 331 rows
```

---

## 📊 Gold Table 1: Vulnerability Priority

This is the main analytics table.

It combines:

- NVD vulnerability metadata
- CVSS severity information
- EPSS exploitation probability
- CISA KEV known exploited status
- Vendor and product information
- Risk score
- Priority level

Important fields:

```text
cve_id
published_date
last_modified_date
vulnerability_status
description
cwe_id
vendor
product_name
cvss_version
cvss_base_score
cvss_base_severity
cvss_vector_string
attack_vector
attack_complexity
privileges_required
user_interaction
confidentiality_impact
integrity_impact
availability_impact
epss_date
epss_score
epss_percentile
is_known_exploited
known_ransomware_campaign_use
date_added
due_date
required_action
risk_score
priority_level
reference_count
affected_entry_count
published_year
published_month
```

Example use cases:

- Find the highest priority vulnerabilities.
- Identify known exploited vulnerabilities.
- Combine severity and exploit probability.
- Support patch prioritisation decisions.

---

## 🏢 Gold Table 2: Vendor Risk Summary

This table aggregates vulnerability risk by vendor and product.

Important fields:

```text
vendor
product_name
total_vulnerabilities
known_exploited_count
average_risk_score
maximum_risk_score
average_epss_score
critical_count
high_count
```

Example use cases:

- Identify vendors with high-risk products.
- Compare products by vulnerability concentration.
- Support vendor-level cyber risk reporting.

---

## 📅 Gold Table 3: Monthly Vulnerability Trends

This table summarises vulnerability activity by year and month.

Important fields:

```text
published_year
published_month
total_cve_count
known_exploited_count
average_cvss_score
average_epss_score
critical_count
high_count
network_attack_vector_count
```

Validated monthly trend output:

```text
2026-06: 6,347 CVEs
2026-07: 1,233 CVEs
```

Example use cases:

- Track vulnerability publication volume over time.
- Monitor monthly critical and high severity counts.
- Identify changes in network-based attack exposure.

---

## 🧬 Gold Table 4: CWE Risk Summary

This table aggregates vulnerability risk by CWE weakness category.

Important fields:

```text
cwe_id
total_vulnerabilities
known_exploited_count
average_risk_score
maximum_risk_score
average_cvss_score
average_epss_score
```

Example use cases:

- Identify common weakness categories.
- Compare CWE groups by risk score.
- Support secure development and remediation planning.

---

## 🧮 Risk Scoring Logic

The project uses a practical scoring approach that combines multiple vulnerability signals.

Main signals:

```text
CVSS base score
EPSS exploit probability
Known exploited status
Reference count
Affected product information
```

Conceptually:

```text
Risk Score = severity signal + exploitability signal + known exploitation signal + exposure context
```

The final risk score is mapped into priority levels:

```text
Critical
High
Medium
Low
```

Validated priority distribution:

```text
Critical: 5
High: 6
Medium: 4,170
Low: 3,399
```

This makes it easier to focus on vulnerabilities that are severe, likely to be exploited, or already known to be exploited.

---

## ✅ Validated Pipeline Output

The lakehouse pipeline has been validated locally.

### Silver Tables

```text
Silver KEV
Rows: 1,631
Columns: 13

Silver EPSS
Rows: 5,000
Columns: 6

Silver NVD
Rows: 7,580
Columns: 26
```

### Gold Tables

```text
Gold Vulnerability Priority
Rows: 7,580
Columns: 33

Gold Vendor Risk Summary
Rows: 2,738
Columns: 9

Gold Monthly Trends
Rows: 2
Columns: 9

Gold CWE Risk Summary
Rows: 331
Columns: 7
```

---

## ⚙️ Tech Stack

| Category | Tools |
|---|---|
| Language | Python |
| Data Processing | PySpark |
| Storage Format | Parquet |
| Data Architecture | Bronze, Silver, Gold Lakehouse |
| Data Sources | CISA KEV, FIRST EPSS, NVD CVE data |
| Development | Git, GitHub, Virtual Environment |
| Future Dashboard | Streamlit, Plotly |
| Future API | FastAPI |
| Future ML | scikit-learn, XGBoost, SHAP, MLflow |

---

## 🚀 How to Run Locally

### 1. Clone the repository

```bash
git clone https://github.com/momo840505/cyber-risk-intelligence-lakehouse.git
cd cyber-risk-intelligence-lakehouse
```

### 2. Create a virtual environment

```bash
python -m venv .venv
```

### 3. Activate the virtual environment

Windows PowerShell:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

### 4. Install dependencies

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -e .
```

### 5. Configure Hadoop winutils on Windows

PySpark on Windows may require `winutils.exe`.

Example setup:

```powershell
$env:HADOOP_HOME = "C:\hadoop"
$env:Path = "C:\hadoop\bin;$env:Path"
where.exe winutils
```

Expected output:

```text
C:\hadoop\bin\winutils.exe
```

### 6. Run data ingestion

```powershell
python .\scripts\run_ingestion.py
```

### 7. Build Silver tables

```powershell
python -m cyber_risk.etl.build_silver_tables
```

### 8. Build Gold tables

```powershell
python -m cyber_risk.etl.build_gold_tables
```

### 9. Inspect lakehouse outputs

```powershell
python .\scripts\inspect_lakehouse.py
```

---

## 🧪 Example Commands Used During Validation

```powershell
python -m cyber_risk.etl.build_silver_tables
python -m cyber_risk.etl.build_gold_tables
python .\scripts\inspect_lakehouse.py
```

Expected folders after successful execution:

```text
data/silver/silver_kev
data/silver/silver_epss
data/silver/silver_nvd

data/gold/vulnerability_priority
data/gold/vendor_risk_summary
data/gold/monthly_vulnerability_trends
data/gold/cwe_risk_summary
```

---

## 📈 Example Insights

Based on the generated Gold tables:

- The lakehouse contains more than 7,500 cleaned vulnerability records.
- Most vulnerabilities are classified as Medium or Low priority.
- A small number of vulnerabilities are classified as Critical or High priority.
- Known exploited vulnerabilities can be separated from general CVE records.
- Vendor-level aggregation helps identify products with concentrated cyber risk.
- CWE summaries help identify common weakness categories.
- Monthly trends show vulnerability publication patterns over time.

---

## 🧭 Current Project Status

Completed:

- Project structure
- Data ingestion modules
- PySpark session setup
- Silver ETL
- Gold ETL
- Lakehouse inspection script
- GitHub repository setup
- Professional README documentation

In progress / planned:

- Streamlit dashboard
- Interactive charts
- Data quality checks
- Machine learning risk classifier
- FastAPI query service
- Automated scheduled ingestion

---

## 🔮 Future Improvements

### Dashboard

Add a Streamlit dashboard for interactive vulnerability exploration.

Planned dashboard pages:

- Executive overview
- Top priority vulnerabilities
- Vendor risk ranking
- CWE risk analysis
- Monthly vulnerability trends
- Known exploited vulnerability explorer

### Data Quality

Add validation checks for:

- Missing CVE IDs
- Duplicate CVE records
- Invalid CVSS score ranges
- Invalid EPSS score ranges
- Null critical fields
- Unexpected schema changes

### Machine Learning

Add a model to classify vulnerability priority using:

- CVSS metrics
- EPSS score
- Attack vector
- Attack complexity
- Vendor/product information
- Known exploitation status

### API Layer

Add FastAPI endpoints such as:

```text
/api/vulnerabilities/top
/api/vendors/risk-summary
/api/cwe/risk-summary
/api/trends/monthly
```

### Automation

Add scheduled ingestion to keep vulnerability intelligence up to date.

---

## 🧑‍💻 Author

**Mo Mo**  
Master of Data Science Student  
GitHub: [@momo840505](https://github.com/momo840505)

---

## 📌 Repository

```text
https://github.com/momo840505/cyber-risk-intelligence-lakehouse
```
