# 🛡️ Cyber Risk Intelligence Lakehouse

!\[Python](https://img.shields.io/badge/Python-3.11%2B-blue)
!\[PySpark](https://img.shields.io/badge/PySpark-ETL-orange)
!\[Lakehouse](https://img.shields.io/badge/Architecture-Bronze%20%7C%20Silver%20%7C%20Gold-green)
!\[Status](https://img.shields.io/badge/Status-ETL%20Pipeline%20Completed-success)

A local cyber risk intelligence lakehouse built with **Python** and **PySpark**.  
The project ingests public cybersecurity vulnerability data, cleans and standardises it into Silver tables, then builds Gold analytics tables for vulnerability prioritisation, vendor risk analysis, CWE weakness summaries, and monthly vulnerability trend monitoring.

\---

## 📌 Project Summary

Security teams often need to decide which vulnerabilities should be patched first.  
However, raw vulnerability feeds are usually fragmented across different sources, such as CVE records, CVSS severity scores, EPSS exploit probability, and known exploited vulnerability lists.

This project solves that problem by building a structured lakehouse pipeline that combines multiple vulnerability intelligence sources into analytics-ready tables.

The pipeline follows a standard data engineering architecture:

```text
Bronze Layer  →  Silver Layer  →  Gold Layer
Raw data         Clean data       Analytics-ready risk intelligence
```

\---

## 🎯 Objectives

The main goals of this project are to:

* Ingest cybersecurity vulnerability data from public sources.
* Store raw data locally in a Bronze layer.
* Clean and standardise data using PySpark.
* Build Silver tables for KEV, EPSS, and NVD vulnerability records.
* Join vulnerability data across sources.
* Create Gold tables for risk prioritisation and reporting.
* Provide a foundation for future dashboard, API, and machine learning extensions.

\---

## 🧠 Why This Project Matters

Not all vulnerabilities have the same level of operational risk.

A vulnerability with a high CVSS score is severe, but it may not be actively exploited.  
A vulnerability with a high EPSS score is more likely to be exploited.  
A vulnerability listed in CISA KEV has already been observed in real-world exploitation.

This project combines these signals to help prioritise vulnerabilities more effectively.

\---

## 🏗️ Lakehouse Architecture

```mermaid
flowchart TD

&#x20;   A\[Public Cybersecurity<br/>Data Sources] --> B\[Bronze Layer<br/>Raw Data]

&#x20;   B --> C\[Silver ETL<br/>PySpark Cleaning]



&#x20;   C --> D\[Silver KEV]

&#x20;   C --> E\[Silver EPSS]

&#x20;   C --> F\[Silver NVD]



&#x20;   D --> G\[Gold ETL<br/>Risk Intelligence]

&#x20;   E --> G

&#x20;   F --> G



&#x20;   G --> H\[Vulnerability<br/>Priority]

&#x20;   G --> I\[Vendor Risk<br/>Summary]

&#x20;   G --> J\[Monthly<br/>Trends]

&#x20;   G --> K\[CWE Risk<br/>Summary]



&#x20;   H --> L\[Future Dashboard<br/>API / ML]

&#x20;   I --> L

&#x20;   J --> L

&#x20;   K --> L```

\---

## 🗂️ Data Sources

This project is designed around three main public cybersecurity intelligence sources:

### 1\. CISA Known Exploited Vulnerabilities

Used to identify vulnerabilities that are known to have been exploited in the real world.

Main information includes:

* CVE ID
* Vendor / project
* Product
* Vulnerability name
* Date added
* Due date
* Required action
* Known ransomware campaign use

\---

### 2\. FIRST EPSS

Used to estimate the probability that a vulnerability may be exploited.

Main information includes:

* CVE ID
* EPSS score
* EPSS percentile
* EPSS date

\---

### 3\. NVD Recent CVE Data

Used to extract vulnerability metadata, CVSS severity, affected products, weakness category, and publication dates.

Main information includes:

* CVE ID
* Published date
* Last modified date
* Vulnerability description
* CWE ID
* Affected vendor
* Affected product
* CVSS score
* CVSS severity
* Attack vector
* Attack complexity
* User interaction
* Impact metrics

\---

## 📁 Project Structure

```text
cyber-risk-intelligence-lakehouse/
│
├── scripts/
│   ├── inspect\_lakehouse.py
│   └── run\_ingestion.py
│
├── src/
│   └── cyber\_risk/
│       ├── \_\_init\_\_.py
│       ├── config.py
│       │
│       ├── ingestion/
│       │   ├── \_\_init\_\_.py
│       │   ├── download\_epss.py
│       │   ├── download\_kev.py
│       │   ├── download\_nvd\_recent.py
│       │   └── http\_client.py
│       │
│       ├── etl/
│       │   ├── \_\_init\_\_.py
│       │   ├── spark\_session.py
│       │   ├── build\_silver\_tables.py
│       │   └── build\_gold\_tables.py
│       │
│       └── quality/
│           └── \_\_init\_\_.py
│
├── .gitignore
├── pyproject.toml
├── requirements.txt
└── README.md
```

\---

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

\---

## 🥈 Silver Layer

The Silver layer contains cleaned and standardised vulnerability data.

Generated Silver tables:

```text
data/silver/silver\_kev
data/silver/silver\_epss
data/silver/silver\_nvd
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
cve\_id
vendor\_project
product
vulnerability\_name
date\_added
due\_date
known\_ransomware\_campaign\_use
required\_action
short\_description
notes
cwe\_list
date\_added\_year
date\_added\_month
```

### Silver EPSS Table

Purpose: clean and standardise exploit probability scores.

Important fields:

```text
cve\_id
epss\_score
epss\_percentile
epss\_date
epss\_year
epss\_month
```

### Silver NVD Table

Purpose: clean and standardise CVE metadata, CVSS severity, CWE category, and affected products.

Important fields:

```text
cve\_id
source\_identifier
published\_datetime
last\_modified\_datetime
vulnerability\_status
description
cwe\_id
affected\_vendor
affected\_product
affected\_entry\_count
reference\_count
cvss\_version
cvss\_base\_score
cvss\_base\_severity
cvss\_vector\_string
attack\_vector
attack\_complexity
privileges\_required
user\_interaction
confidentiality\_impact
integrity\_impact
availability\_impact
published\_date
last\_modified\_date
published\_year
published\_month
```

\---

## 🥇 Gold Layer

The Gold layer contains analytics-ready risk intelligence tables.

Generated Gold tables:

```text
data/gold/vulnerability\_priority
data/gold/vendor\_risk\_summary
data/gold/monthly\_vulnerability\_trends
data/gold/cwe\_risk\_summary
```

Validated Gold output:

```text
Gold Vulnerability Priority: 7,580 rows
Gold Vendor Risk Summary: 2,738 rows
Gold Monthly Trends: 2 rows
Gold CWE Risk Summary: 331 rows
```

\---

## 📊 Gold Table 1: Vulnerability Priority

This is the main analytics table.

It combines:

* NVD vulnerability metadata
* CVSS severity information
* EPSS exploitation probability
* CISA KEV known exploited status
* Vendor and product information
* Risk score
* Priority level

Important fields:

```text
cve\_id
published\_date
last\_modified\_date
vulnerability\_status
description
cwe\_id
vendor
product\_name
cvss\_version
cvss\_base\_score
cvss\_base\_severity
cvss\_vector\_string
attack\_vector
attack\_complexity
privileges\_required
user\_interaction
confidentiality\_impact
integrity\_impact
availability\_impact
epss\_date
epss\_score
epss\_percentile
is\_known\_exploited
known\_ransomware\_campaign\_use
date\_added
due\_date
required\_action
risk\_score
priority\_level
reference\_count
affected\_entry\_count
published\_year
published\_month
```

Example use cases:

* Find the highest priority vulnerabilities.
* Identify known exploited vulnerabilities.
* Combine severity and exploit probability.
* Support patch prioritisation decisions.

\---

## 🏢 Gold Table 2: Vendor Risk Summary

This table aggregates vulnerability risk by vendor and product.

Important fields:

```text
vendor
product\_name
total\_vulnerabilities
known\_exploited\_count
average\_risk\_score
maximum\_risk\_score
average\_epss\_score
critical\_count
high\_count
```

Example use cases:

* Identify vendors with high-risk products.
* Compare products by vulnerability concentration.
* Support vendor-level cyber risk reporting.

\---

## 📅 Gold Table 3: Monthly Vulnerability Trends

This table summarises vulnerability activity by year and month.

Important fields:

```text
published\_year
published\_month
total\_cve\_count
known\_exploited\_count
average\_cvss\_score
average\_epss\_score
critical\_count
high\_count
network\_attack\_vector\_count
```

Validated monthly trend output:

```text
2026-06: 6,347 CVEs
2026-07: 1,233 CVEs
```

Example use cases:

* Track vulnerability publication volume over time.
* Monitor monthly critical and high severity counts.
* Identify changes in network-based attack exposure.

\---

## 🧬 Gold Table 4: CWE Risk Summary

This table aggregates vulnerability risk by CWE weakness category.

Important fields:

```text
cwe\_id
total\_vulnerabilities
known\_exploited\_count
average\_risk\_score
maximum\_risk\_score
average\_cvss\_score
average\_epss\_score
```

Example use cases:

* Identify common weakness categories.
* Compare CWE groups by risk score.
* Support secure development and remediation planning.

\---

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

\---

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

\---

## ⚙️ Tech Stack

|Category|Tools|
|-|-|
|Language|Python|
|Data Processing|PySpark|
|Storage Format|Parquet|
|Data Architecture|Bronze, Silver, Gold Lakehouse|
|Data Sources|CISA KEV, FIRST EPSS, NVD CVE data|
|Development|Git, GitHub, Virtual Environment|
|Future Dashboard|Streamlit, Plotly|
|Future API|FastAPI|
|Future ML|scikit-learn, XGBoost, SHAP, MLflow|

\---

## 🚀 How to Run Locally

### 1\. Clone the repository

```bash
git clone https://github.com/momo840505/cyber-risk-intelligence-lakehouse.git
cd cyber-risk-intelligence-lakehouse
```

### 2\. Create a virtual environment

```bash
python -m venv .venv
```

### 3\. Activate the virtual environment

Windows PowerShell:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\\.venv\\Scripts\\Activate.ps1
```

### 4\. Install dependencies

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -e .
```

### 5\. Configure Hadoop winutils on Windows

PySpark on Windows may require `winutils.exe`.

Example setup:

```powershell
$env:HADOOP\_HOME = "C:\\hadoop"
$env:Path = "C:\\hadoop\\bin;$env:Path"
where.exe winutils
```

Expected output:

```text
C:\\hadoop\\bin\\winutils.exe
```

### 6\. Run data ingestion

```powershell
python .\\scripts\\run\_ingestion.py
```

### 7\. Build Silver tables

```powershell
python -m cyber\_risk.etl.build\_silver\_tables
```

### 8\. Build Gold tables

```powershell
python -m cyber\_risk.etl.build\_gold\_tables
```

### 9\. Inspect lakehouse outputs

```powershell
python .\\scripts\\inspect\_lakehouse.py
```

\---

## 🧪 Example Commands Used During Validation

```powershell
python -m cyber\_risk.etl.build\_silver\_tables
python -m cyber\_risk.etl.build\_gold\_tables
python .\\scripts\\inspect\_lakehouse.py
```

Expected folders after successful execution:

```text
data/silver/silver\_kev
data/silver/silver\_epss
data/silver/silver\_nvd

data/gold/vulnerability\_priority
data/gold/vendor\_risk\_summary
data/gold/monthly\_vulnerability\_trends
data/gold/cwe\_risk\_summary
```

\---

## 📈 Example Insights

Based on the generated Gold tables:

* The lakehouse contains more than 7,500 cleaned vulnerability records.
* Most vulnerabilities are classified as Medium or Low priority.
* A small number of vulnerabilities are classified as Critical or High priority.
* Known exploited vulnerabilities can be separated from general CVE records.
* Vendor-level aggregation helps identify products with concentrated cyber risk.
* CWE summaries help identify common weakness categories.
* Monthly trends show vulnerability publication patterns over time.

\---

## 🧭 Current Project Status

Completed:

* Project structure
* Data ingestion modules
* PySpark session setup
* Silver ETL
* Gold ETL
* Lakehouse inspection script
* GitHub repository setup
* Professional README documentation

In progress / planned:

* Streamlit dashboard
* Interactive charts
* Data quality checks
* Machine learning risk classifier
* FastAPI query service
* Automated scheduled ingestion

\---

## 🔮 Future Improvements

### Dashboard

Add a Streamlit dashboard for interactive vulnerability exploration.

Planned dashboard pages:

* Executive overview
* Top priority vulnerabilities
* Vendor risk ranking
* CWE risk analysis
* Monthly vulnerability trends
* Known exploited vulnerability explorer

### Data Quality

Add validation checks for:

* Missing CVE IDs
* Duplicate CVE records
* Invalid CVSS score ranges
* Invalid EPSS score ranges
* Null critical fields
* Unexpected schema changes

### Machine Learning

Add a model to classify vulnerability priority using:

* CVSS metrics
* EPSS score
* Attack vector
* Attack complexity
* Vendor/product information
* Known exploitation status

### API Layer

Add FastAPI endpoints such as:

```text
/api/vulnerabilities/top
/api/vendors/risk-summary
/api/cwe/risk-summary
/api/trends/monthly
```

### 

