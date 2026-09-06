# Cyber Risk Intelligence Lakehouse + AI Remediation Copilot

[![Live Dashboard](https://img.shields.io/badge/Live%20Dashboard-Open%20App-FF4B4B?logo=streamlit&logoColor=white)](https://cyber-risk-intelligence-momo.streamlit.app)
[![Python CI](https://github.com/momo840505/cyber-risk-intelligence-lakehouse/actions/workflows/python-ci.yml/badge.svg)](https://github.com/momo840505/cyber-risk-intelligence-lakehouse/actions/workflows/python-ci.yml)
[![Docker Build](https://github.com/momo840505/cyber-risk-intelligence-lakehouse/actions/workflows/docker-build.yml/badge.svg)](https://github.com/momo840505/cyber-risk-intelligence-lakehouse/actions)
[![Terraform Validate](https://github.com/momo840505/cyber-risk-intelligence-lakehouse/actions/workflows/terraform-validate.yml/badge.svg)](https://github.com/momo840505/cyber-risk-intelligence-lakehouse/actions)
![Python](https://img.shields.io/badge/Python-3.11-blue)
![PySpark](https://img.shields.io/badge/PySpark-Lakehouse-orange)
![dbt](https://img.shields.io/badge/dbt-Analytics-red)
![FastAPI](https://img.shields.io/badge/FastAPI-API-green)
![Docker](https://img.shields.io/badge/Docker-Ready-blue)
![Terraform](https://img.shields.io/badge/Terraform-IaC-purple)
![AWS](https://img.shields.io/badge/AWS-Architecture-orange)
![MLflow](https://img.shields.io/badge/MLflow-Tracking-lightgrey)
![SHAP](https://img.shields.io/badge/SHAP-Explainability-purple)

## Overview

This project is an end-to-end **Cyber Risk Intelligence Platform** that combines data engineering, analytics engineering, machine learning, API development, RAG-based remediation guidance, monitoring, Docker deployment readiness, and AWS infrastructure-as-code design.

It ingests public cyber risk data, builds a PySpark lakehouse, transforms analytics marts with dbt and DuckDB, trains a vulnerability priority classifier, explains model behaviour with SHAP, exposes risk intelligence through FastAPI, generates defensive remediation plans using local RAG retrieval, tracks API usage through monitoring logs, provides Docker deployment support, and includes a Terraform AWS architecture template.

The project is designed as a portfolio-ready platform for roles such as:

- Data Engineer
- Analytics Engineer
- Data Scientist
- Machine Learning Engineer
- AI Engineer
- Cloud Data Engineer
- Security Data Analyst

---

## Current Status

```text
✅ Phase 1: PySpark Cyber Risk Lakehouse
✅ Phase 2: dbt + DuckDB Analytics Layer
✅ Phase 3: ML Priority Classifier + SHAP + MLflow
✅ Phase 4: FastAPI Risk Intelligence API
✅ Phase 5: RAG Remediation Copilot
✅ Phase 6: API Monitoring and Observability
✅ Phase 7: Docker Deployment Readiness
✅ Phase 8: Terraform + AWS Architecture Template
```

---

## Architecture

```mermaid
flowchart TD
    A[Public Cyber Risk Sources] --> B[Bronze Layer]
    B --> C[Silver Layer]
    C --> D[Gold Layer]

    D --> E[dbt + DuckDB Analytics Marts]
    E --> F[Streamlit Dashboard]
    E --> G[ML Exploitation-Likelihood Classifier]
    G --> H[SHAP Explainability]
    G --> I[MLflow Tracking]

    E --> J[FastAPI Risk Intelligence API]
    G --> J

    K[Local Remediation Knowledge Base] --> L[RAG Retrieval]
    E --> L
    L --> M[AI Remediation Copilot]
    M --> J

    J --> N[API Monitoring Middleware]
    N --> O[API Usage Logs]
    O --> P[Monitoring Reports]

    J --> Q[Docker Container]
    Q --> R[Docker Compose Deployment]
    Q --> S[API Smoke Test]
    Q --> T[Docker Build CI]

    Q -.->|planned, not yet applied| U[AWS ECR]
    U -.-> V[AWS ECS Fargate]
    V -.-> W[Application Load Balancer]
    V -.-> X[CloudWatch Logs and Dashboard]
    Y[S3 Lakehouse Storage Template] -.-> V
    Z[Terraform IaC] -.-> U
    Z -.-> V
    Z -.-> W
    Z -.-> X
    Z -.-> Y
```

Solid arrows are running today (Docker Compose, locally). Dashed arrows (AWS ECR
onward) are the Terraform-templated target architecture that has **not**
been applied yet -- see 'Limitations' and 'Future Improvements' below.

---

## Data Sources

The platform uses public cyber risk intelligence sources:

- **CISA Known Exploited Vulnerabilities (KEV)**  
  Used to identify vulnerabilities with evidence of active exploitation.

- **EPSS vulnerability scoring data**  
  Used to enrich vulnerabilities with exploit probability signals when available.

- **NVD CVE data**  
  Used for CVE metadata, CVSS severity, CWE information, affected vendor/product information, and vulnerability descriptions.
  Ingestion currently pulls a **rolling 30-day window** of recently-published CVEs
  (`download_recent_nvd_cves(days_back=30)`), not full NVD history, so the dataset's
  time span grows only as the pipeline is re-run over time -- see 'Limitations' below
  for what this means for the trend charts and the model's label distribution.

---

## Project Structure

```text
cyber-risk-intelligence-lakehouse/
├── api/
│   └── main.py
│
├── app/
│   └── dashboard.py
│
├── assets/
│   ├── dashboard_overview.png
│   ├── dashboard_risk_analysis.png
│   └── dashboard_top_vulnerabilities.png
│
├── data/
│   ├── bronze/
│   ├── silver/
│   └── gold/
│
├── dbt/
│   └── cyber_risk_dbt/
│       ├── dbt_project.yml
│       └── models/
│           ├── staging/
│           └── marts/
│
├── infrastructure/
│   └── aws/
│       ├── README.md
│       ├── versions.tf
│       ├── variables.tf
│       ├── main.tf
│       ├── networking.tf
│       ├── security_groups.tf
│       ├── storage.tf
│       ├── ecr.tf
│       ├── iam.tf
│       ├── ecs.tf
│       ├── monitoring.tf
│       ├── outputs.tf
│       └── terraform.tfvars.example
│
├── ml/
│   └── train_priority_model.py
│
├── models/
│   └── exploitation_likelihood_classifier.joblib
│
├── monitoring/
│   └── api_usage_log.csv
│
├── rag/
│   ├── remediation_copilot.py
│   └── knowledge_base/
│       ├── cisa_kev_remediation.md
│       ├── cvss_prioritisation.md
│       ├── cwe_remediation.md
│       ├── emergency_response.md
│       └── vulnerability_management.md
│
├── reports/
│   ├── data_quality_report.csv
│   ├── model_metrics.json
│   ├── classification_report.csv
│   ├── confusion_matrix.csv
│   ├── feature_importance.csv
│   ├── feature_importance.png
│   ├── shap_feature_importance.png
│   ├── copilot_eval_report.csv
│   ├── copilot_eval_summary.json
│   ├── api_endpoint_summary.csv
│   └── api_monitoring_summary.json
│
├── scripts/
│   ├── run_pipeline.py
│   ├── run_ingestion.py
│   ├── validate_lakehouse.py
│   ├── inspect_lakehouse.py
│   ├── build_analytics_database.py
│   ├── run_dbt.py
│   ├── run_ml.py
│   ├── run_api.py
│   ├── run_copilot.py
│   ├── evaluate_copilot.py
│   ├── generate_monitoring_report.py
│   ├── smoke_test_api.py
│   └── validate_terraform_template.py
│
├── .github/
│   └── workflows/
│       ├── python-ci.yml
│       ├── docker-build.yml
│       └── terraform-validate.yml
│
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── requirements-api.txt
├── .dockerignore
├── .gitignore
└── README.md
```

---

## Lakehouse Layers

### Bronze Layer

The Bronze layer stores raw ingested cyber risk data from public sources.

Typical inputs:

- CISA KEV records
- EPSS vulnerability scoring data
- NVD CVE records

### Silver Layer

The Silver layer cleans, normalises, and prepares records for analytics.

Typical transformations:

- Standardised CVE IDs
- Normalised CVSS fields
- Parsed CWE IDs
- Vendor and product extraction
- Known exploited vulnerability flags
- Reference and affected product counts

### Gold Layer

The Gold layer produces analytics-ready datasets.

Gold outputs include:

- `vulnerability_priority`
- `vendor_risk_summary`
- `monthly_vulnerability_trends`
- `cwe_risk_summary`

---

## Data Quality Validation

The project includes automated validation for the Gold lakehouse outputs.

Validation checks include:

- Required columns exist
- CVE IDs are not missing
- CVE IDs are unique where expected
- CVSS scores are within valid range
- EPSS scores are within valid range when available
- Risk scores are within expected bounds
- Priority levels are valid
- Known exploited flags are binary
- Vendor risk summary tables contain required fields

Run validation:

```powershell
python .\scripts\validate_lakehouse.py
```

Example result:

```text
PASS: 18
WARN: 0
FAIL: 0
Data quality validation completed successfully.
```

---

## dbt Analytics Layer

The dbt layer builds staging and mart models on top of a DuckDB analytics database.

### dbt Models

Staging models:

- `stg_vulnerability_priority`
- `stg_vendor_risk_summary`
- `stg_monthly_vulnerability_trends`
- `stg_cwe_risk_summary`

Mart models:

- `mart_vulnerability_priority`
- `mart_vendor_risk_summary`
- `mart_monthly_vulnerability_trends`
- `mart_cwe_risk_summary`

Run dbt:

```powershell
python .\scripts\run_dbt.py
```

Example dbt result:

```text
Done. PASS=26 WARN=0 ERROR=0 SKIP=0 NO-OP=0 TOTAL=26
```

Serve dbt docs:

```powershell
cd dbt\cyber_risk_dbt
dbt docs generate
dbt docs serve
```

---

## Machine Learning: Exploitation-Likelihood Classifier

The ML component trains a classifier that predicts whether a CVE is likely
to become a **CISA Known Exploited Vulnerability (KEV)** entry, using only
metadata available at CVE publication time.

### A design note on target leakage (and why the target changed)

An earlier version of this model predicted `priority_level`, a label
computed in the ETL layer as a fixed linear combination of CVSS score,
EPSS percentile, and a handful of CVSS vector fields, thresholded into
four bands (see `src/cyber_risk/etl/build_gold_tables.py`). Those exact
same fields were also being used as the model's training features. That
meant the "classifier" wasn't learning anything from the data -- it was
using 300 decision trees to re-derive a formula it already had every
input to compute directly, which is why accuracy came out around **98.6%**
(reported below, kept here deliberately as a worked example of the
problem, not a result to be proud of).

The fix: predict `is_known_exploited` instead. Unlike `priority_level`,
KEV membership is a genuinely independent, forward-looking label --
CISA adds a CVE to the list only after real-world exploitation is
observed, which has nothing to do with how the CVSS/EPSS fields were
combined in this project's own ETL code. `epss_score` / `epss_percentile`
are also excluded from the features: EPSS is itself a model for the same
question, so using its output as an input feature would just be
re-packaging someone else's prediction rather than a genuine independent
signal.

### Target

```text
is_known_exploited: 0 (not in KEV)  |  1 (in KEV)
```

### Features

Deliberately limited to information available at CVE publication time,
before anyone knows whether the vulnerability will be exploited:

- `cvss_base_score`
- `cvss_base_severity`
- `attack_vector`
- `attack_complexity`
- `privileges_required`
- `user_interaction`
- `cwe_id`
- `reference_count`
- `affected_entry_count`
- `published_month`

`risk_score`, `priority_level`, `epss_score`, and `epss_percentile` are
intentionally **not** used as features -- see the note above.

### Current Model Metrics

KEV membership is rare (most CVEs are never observed being exploited), so
the headline number here is `cv_roc_auc_out_of_fold`, not plain `accuracy`.
A model that always predicts "not exploited" already scores close to
`baseline_accuracy_always_majority_class` without learning anything, and a
single train/test split only holds a handful of positive examples in the
test set -- across two actual pipeline runs, single-split `roc_auc` swung
from 0.47 to 0.75 purely depending on which positives landed in that split.
`cv_roc_auc_out_of_fold` comes from 5-fold stratified cross-validation and
pools out-of-fold predictions across every known-exploited CVE in the full
dataset instead, and has stayed in the 0.79-0.80 range across both runs so
far -- that's the one worth trusting.

Two other things reported alongside the classification metrics:

- `precision_at_k` / `recall_at_k` (K = 10, 20, 50): of the top-K CVEs
  ranked by predicted probability, how many are actually known-exploited.
  This model's real use case is ranking a review queue, not a single
  yes/no call, so precision@K matches that use case better than a global
  metric like average precision does.
- `tuned_threshold`: the probability cutoff that maximises F1 on the
  out-of-fold predictions, used by the `/predict-exploitation-likelihood`
  API endpoint instead of the sklearn default of 0.5 (see
  `ml/train_priority_model.py` and `api/main.py::load_decision_threshold`).
  With only 15 positive examples total, treat this as a reasonable
  starting point, not a precisely optimised number -- it can move on the
  next ingestion run.

Run the ML workflow and copy the real numbers from
`reports/model_metrics.json` into the block below:

```powershell
python .\scripts\run_ml.py
```

```json
{
  "training_rows": 8629,
  "test_rows": 2877,
  "positive_rate_train": 0.0013,
  "positive_rate_test": 0.0014,
  "baseline_accuracy_always_majority_class": 0.9986,
  "accuracy": 0.976,
  "balanced_accuracy": 0.6135,
  "macro_f1": 0.508,
  "weighted_f1": 0.9865,
  "roc_auc": 0.7541,
  "average_precision": 0.0094,
  "classes": [0, 1],
  "cv_folds": 5,
  "cv_roc_auc_out_of_fold": 0.7941,
  "cv_average_precision_out_of_fold": 0.0061,
  "tuned_threshold": 0.3862,
  "tuned_threshold_precision": 0.0099,
  "tuned_threshold_recall": 0.6,
  "tuned_threshold_f1": 0.0194,
  "precision_at_10": 0.0,
  "recall_at_10": 0.0,
  "precision_at_20": 0.0,
  "recall_at_20": 0.0,
  "precision_at_50": 0.0,
  "recall_at_50": 0.0
}
```

Only 15 of 11,506 CVEs in this training set are known-exploited (0.13%), so
average precision stays low even alongside a decent ROC-AUC -- at this base
rate a well-ranking model still produces many false positives for every
true positive it flags.

`precision_at_10/20/50` coming out at exactly 0.0 in this run is a real,
checked result, not a bug -- and it's the most honest finding in this whole
section. Looking at the out-of-fold ranks directly: the best-placed
known-exploited CVE in this run landed at rank ~190 out of 11,506 (top ~2%,
genuinely better than random), but every one of the top ~190 spots was
taken by a CRITICAL-severity, CVSS 9.3-9.8 CVE that was **never** exploited.
CVSS/CWE metadata alone can flag "this looks dangerous," but a few hundred
other CVEs look equally dangerous by that same metadata and weren't
exploited -- there's nothing in this feature set to break that tie. That's
also exactly the gap a behavioural signal like EPSS is built to fill
(threat-intel chatter, public PoC availability, actual attacker interest),
which is precisely why EPSS is excluded as a feature here rather than
reused (see the target-leakage note above) -- this model and EPSS are
answering a related but different question, and this result is a concrete
illustration of the ceiling that static CVSS/CWE metadata runs into on its
own. Read this model as a broad risk-scoring signal, not a precise "top N
to review" tool, until it's paired with a behavioural signal or richer
features (e.g. text from the CVE description or vendor advisories).

Note: `reports/data_quality_report.csv` and the raw
`data/gold/vulnerability_priority` parquet can show a different row count
than the training-set figures above -- that's expected, not a bug: rows
missing a required feature (e.g. no CVSS score yet) get dropped before
training. What should NOT drift independently is `data_quality_report.csv`
vs the Gold parquet row count themselves -- re-run the full pipeline
(`python .\scripts\run_pipeline.py` then `python .\scripts\run_ml.py`) in
one sitting before quoting any of these numbers together (e.g. in an
interview or on a resume), so they all reflect the same ingestion
snapshot.

---

## MLflow Tracking

The ML workflow logs experiment metadata with MLflow.

Tracked outputs include:

- Model metrics
- Classifier configuration
- Model artifact
- Feature importance
- SHAP explainability outputs

MLflow artifacts are stored locally and excluded from Git where appropriate.

---

## Model Explainability with SHAP

The project includes two explainability outputs:

```text
reports/feature_importance.png
reports/shap_feature_importance.png
```

### Feature Importance

![Feature Importance](reports/feature_importance.png)

The feature importance plot shows which input variables the classifier uses most often to split and classify vulnerabilities.

### SHAP Feature Importance

![SHAP Feature Importance](reports/shap_feature_importance.png)

The SHAP plot explains which features have the strongest average impact on model predictions.

Important features include (from `reports/shap_feature_importance.png`, regenerated after the target-leakage fix below). The exact ranking shifts a little between pipeline runs, because ingestion only pulls a rolling 30-day NVD window each time (see 'Limitations' below) -- as of the most recent run:

- CVSS base score
- Reference count
- CVSS severity (medium / critical / high)
- Privileges required (none / low)
- User interaction (none)
- Publication month -- worth calling out on its own: this feature being predictive at all is partly an artifact of the narrow ingestion window (very recently published CVEs haven't had time to be confirmed exploited yet), not a genuine causal signal. See 'Limitations' below.

CWE category (e.g. CWE-78 command injection, CWE-94 code injection) also
ranks highly on the RandomForest's own impurity-based `reports/feature_importance.csv`,
though it moves in and out of the SHAP top 10 between runs.

Note: `is_known_exploited` (the CISA KEV flag) is the model's **target**, not a feature -- it is deliberately excluded from the training feature set to avoid target leakage (see 'A design note on target leakage' above), so it will never appear in this list.

---

## FastAPI Risk Intelligence API

The project exposes cyber risk intelligence through FastAPI.

### Local API URL

```text
http://127.0.0.1:8001
```

### Swagger UI

```text
http://127.0.0.1:8001/docs
```

### Metrics Endpoint

```text
http://127.0.0.1:8001/metrics
```

Start the API locally:

```powershell
python .\scripts\run_api.py
```

The script starts FastAPI on port `8001` by default.

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/` | Service metadata |
| GET | `/health` | Health check for analytics DB, model, and monitoring log |
| GET | `/metrics` | API usage and response time metrics |
| GET | `/vulnerabilities/top` | Top vulnerabilities ranked by risk |
| GET | `/vulnerabilities/{cve_id}` | CVE-level detail lookup |
| GET | `/vendors/risk-summary` | Vendor and product risk summary |
| GET | `/cwe/risk-summary` | CWE-level risk summary |
| GET | `/trends/monthly` | Monthly vulnerability trend summary |
| POST | `/predict-exploitation-likelihood` | Predicts KEV-exploitation likelihood from static CVE metadata |
| GET | `/remediation/{cve_id}` | RAG-based remediation plan |

---

## Example API Usage

### Health Check

```powershell
Invoke-RestMethod http://127.0.0.1:8001/health | ConvertTo-Json -Depth 5
```

Example response:

```json
{
  "status": "ok",
  "analytics_database_exists": true,
  "model_exists": true,
  "monitoring_log_exists": true
}
```

### Top Vulnerabilities

```powershell
Invoke-RestMethod "http://127.0.0.1:8001/vulnerabilities/top?limit=5"
```

### CVE Lookup

```powershell
Invoke-RestMethod "http://127.0.0.1:8001/vulnerabilities/CVE-2016-20068"
```

### Exploitation-Likelihood Prediction

Note there is no `is_known_exploited`, `epss_score`, or `epss_percentile`
in the request body -- those are the target and the leakage-prone fields
excluded from the model. See "Machine Learning: Exploitation-Likelihood
Classifier" above.

```powershell
$body = @{
    cvss_base_score = 9.8
    reference_count = 5
    affected_entry_count = 1
    published_month = 7
    cvss_base_severity = "CRITICAL"
    attack_vector = "NETWORK"
    attack_complexity = "LOW"
    privileges_required = "NONE"
    user_interaction = "NONE"
    cwe_id = "CWE-434"
} | ConvertTo-Json

Invoke-RestMethod `
    -Uri "http://127.0.0.1:8001/predict-exploitation-likelihood" `
    -Method Post `
    -ContentType "application/json" `
    -Body $body |
ConvertTo-Json -Depth 5
```

---

## RAG Remediation Copilot

The project includes a local retrieval-based remediation copilot.

It does not require an external LLM API key.

The copilot retrieves defensive guidance from a local remediation knowledge base and generates context-aware remediation plans using:

- CVE metadata
- CVSS severity
- Known exploited status
- Attack vector
- CWE weakness type
- Priority level
- Local security remediation playbooks

### Knowledge Base

```text
rag/knowledge_base/
├── cisa_kev_remediation.md
├── cvss_prioritisation.md
├── cwe_remediation.md
├── emergency_response.md
└── vulnerability_management.md
```

### Example Remediation API

```powershell
Invoke-RestMethod "http://127.0.0.1:8001/remediation/CVE-2026-48908" |
ConvertTo-Json -Depth 8
```

Example output includes:

```text
priority_level
risk_score
urgency
recommended_sla
vulnerability_context
why_this_priority
recommended_actions
retrieved_sources
safety_note
```

### Security-Safe Behaviour

The copilot is designed for defensive remediation guidance only.

It does not provide:

- Exploit instructions
- Offensive payloads
- Attack execution steps
- Weaponisation guidance

---

## Copilot Evaluation

The evaluation script checks the copilot on two different levels:
`pass_rate` (did it run and return something) and `mean_quality_score`
(does what it returned actually reflect this specific CVE).

`pass_rate` only checks that the copilot found the CVE and returned a
non-empty actions list, source list, safety note, and priority explanation.
Because `build_context_aware_actions` always appends a set of
urgency-appropriate baseline actions regardless of which CVE is queried, a
100% pass rate mostly just confirms the pipeline runs end-to-end without
crashing -- it's a completeness/smoke check, not a quality measure.

`mean_quality_score` is a rougher but more useful signal, averaged per case
from three checks (only counting the ones that actually apply to that
case):

- `has_cwe_specific_guidance` -- did the actions include anything beyond
  the fixed baseline (only possible for the 4 CWEs currently mapped in
  `CWE_ACTIONS`; a case whose CWE has no mapping isn't counted against
  this, since the copilot has no way to fill that gap yet)
- `has_relevant_retrieval` -- did the RAG step actually find a
  knowledge-base doc with real vocabulary overlap (cosine similarity
  >= 0.05), rather than just returning its highest-scoring doc regardless
  of how weak that match is
- `has_context_appropriate_source` -- for known-exploited or
  Emergency-urgency CVEs, did retrieval surface the specific doc that
  `filter_documents_for_context` is designed to prioritise for that
  situation (`cisa_kev_remediation.md` / `emergency_response.md`)

This is still a heuristic, not human-graded ground truth: it checks that
the system behaved the way it's designed to, not that the remediation
advice is genuinely good. A real quality bar would need manual grading or
an LLM-as-judge step -- listed under Future Improvements.

Run evaluation (this writes the real numbers to
`reports/copilot_eval_summary.json` -- copy them from there rather than
from the illustrative shape below):

```powershell
python .\scripts\evaluate_copilot.py
```

Output shape:

```json
{
  "evaluated_cases": 5,
  "passed_cases": 5,
  "failed_cases": 0,
  "pass_rate": 1.0,
  "pass_rate_note": "completeness check only -- see mean_quality_score",
  "cases_with_cwe_mapping": "<int: how many of the 5 CVEs have a CWE_ACTIONS entry>",
  "cwe_specific_guidance_rate": "<float or null if cases_with_cwe_mapping is 0>",
  "cases_with_relevant_retrieval": "<int>",
  "cases_with_context_appropriate_source": "<int>",
  "mean_quality_score": "<float>"
}
```

Reports:

```text
reports/copilot_eval_report.csv
reports/copilot_eval_summary.json
```

---

## API Monitoring and Observability

Phase 6 adds lightweight API monitoring.

The FastAPI middleware records:

- Timestamp
- HTTP method
- Request path
- Status code
- Response time
- Client host

Runtime log:

```text
monitoring/api_usage_log.csv
```

This runtime log is excluded from Git.

### Metrics Endpoint

```powershell
Invoke-RestMethod http://127.0.0.1:8001/metrics |
ConvertTo-Json -Depth 6
```

Example metrics:

```json
{
  "total_requests": 10,
  "error_count": 0,
  "error_rate": 0.0,
  "average_response_time_ms": 17.106,
  "p95_response_time_ms": 28.373,
  "unique_paths": 9
}
```

### Generate Monitoring Report

```powershell
python .\scripts\generate_monitoring_report.py
```

Generated reports:

```text
reports/api_endpoint_summary.csv
reports/api_monitoring_summary.json
```

---

## Docker Deployment Readiness

Phase 7 adds Docker support for the FastAPI risk intelligence service.

### Docker Files

```text
Dockerfile
docker-compose.yml
.dockerignore
requirements-api.txt
scripts/smoke_test_api.py
.github/workflows/docker-build.yml
```

### Port Mapping

The container runs FastAPI internally on port `8000`.

The local machine accesses the container through port `8001`.

```text
Local machine: http://127.0.0.1:8001
Docker container: http://0.0.0.0:8000
Port mapping: 8001:8000
```

### Build Docker Image

```powershell
docker compose build
```

### Start Docker API

```powershell
docker compose up -d
```

### Check Container Status

```powershell
docker compose ps
```

Expected status:

```text
Up ... (healthy)
0.0.0.0:8001->8000/tcp
```

### Test Docker API

```powershell
Invoke-RestMethod http://127.0.0.1:8001/health | ConvertTo-Json -Depth 5
```

### Run API Smoke Test

```powershell
python .\scripts\smoke_test_api.py
```

Expected result:

```text
========== API Smoke Test ==========
Base URL: http://127.0.0.1:8001
PASS /health
PASS /vulnerabilities/top
PASS /remediation/CVE-XXXX-XXXXX   # actual top-risk CVE ID, picked live from /vulnerabilities/top
PASS /metrics

All smoke tests passed.
```

### Stop Docker API

```powershell
docker compose down
```

---

## AWS Terraform Architecture Template

Phase 8 adds an AWS infrastructure-as-code template.

This phase is designed as a **cloud architecture and Terraform validation layer**.

It does not require running paid AWS resources during local development.

Do not run `terraform apply` unless you understand the AWS resources and possible costs.

### Terraform Folder

```text
infrastructure/aws/
├── README.md
├── versions.tf
├── variables.tf
├── main.tf
├── networking.tf
├── security_groups.tf
├── storage.tf
├── ecr.tf
├── iam.tf
├── ecs.tf
├── monitoring.tf
├── outputs.tf
└── terraform.tfvars.example
```

### AWS Architecture Covered

The Terraform template defines:

- VPC
- Public subnets
- Internet gateway
- Route table
- Application Load Balancer
- ECS Fargate cluster
- ECS service
- ECS task definition
- ECR container registry
- S3 lakehouse bucket
- IAM task execution role
- IAM task role with S3 access
- CloudWatch log group
- CloudWatch dashboard
- Security groups for ALB and ECS tasks

### Intended Deployment Design

```text
Docker image
→ Amazon ECR
→ ECS Fargate service
→ Application Load Balancer
→ CloudWatch logs and metrics

Lakehouse artifacts
→ Amazon S3

Infrastructure
→ Terraform
```

### Terraform Local Validation

If Terraform is installed locally:

```powershell
terraform -chdir=infrastructure/aws fmt -recursive
terraform -chdir=infrastructure/aws init -backend=false
terraform -chdir=infrastructure/aws validate
```

Expected result:

```text
Success! The configuration is valid.
```

### Python Template Validation

If Terraform is not installed locally, validate the template structure with Python:

```powershell
python .\scripts\validate_terraform_template.py
```

Expected result:

```text
Terraform template validation completed successfully.
```

### Terraform CI

The repository includes:

```text
.github/workflows/terraform-validate.yml
```

The workflow runs:

- `terraform fmt -check -recursive`
- `terraform init -backend=false`
- `terraform validate`

This validates the infrastructure template on GitHub Actions without applying resources.

---

## Streamlit Dashboard

The project also includes a Streamlit dashboard for cyber risk exploration.

👉 [Open the live dashboard](https://cyber-risk-intelligence-momo.streamlit.app)

The deployed dashboard reads a small, git-committed snapshot of the Gold layer
(`app/data/gold/`, produced by `scripts/prepare_dashboard_data.py`) rather than
the full local lakehouse, since Streamlit Community Cloud has no Spark/JVM
runtime to rebuild it. See that script's docstring for details.

Run locally instead:

```powershell
python -m streamlit run app\dashboard.py
```

Dashboard screenshots:

![Dashboard Overview](assets/dashboard_overview.png)

![Dashboard Risk Analysis](assets/dashboard_risk_analysis.png)

![Dashboard Top Vulnerabilities](assets/dashboard_top_vulnerabilities.png)

---

## One-Command Pipeline

Run the full local pipeline:

```powershell
python .\scripts\run_pipeline.py
```

The pipeline executes:

```text
Bronze ingestion
→ Build Silver tables
→ Build Gold tables
→ Validate Gold tables
→ Build dbt analytics marts
→ Inspect lakehouse outputs
```

---

## Local Setup

### 1. Clone Repository

```powershell
git clone https://github.com/momo840505/cyber-risk-intelligence-lakehouse.git
cd cyber-risk-intelligence-lakehouse
```

### 2. Create Virtual Environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install Dependencies

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -e .
```

The last line installs this repository's own `src/cyber_risk` package in editable mode.
Without it, scripts that do `from cyber_risk...` (e.g. `scripts/run_ingestion.py`) fail with
`ModuleNotFoundError: No module named 'cyber_risk'` -- CI already does this install step (see
`.github/workflows/python-ci.yml`), this just brings local setup in line with it.

### 4. Configure Hadoop on Windows

PySpark on Windows may require `winutils.exe`.

Example configuration:

```powershell
$env:HADOOP_HOME = "C:\hadoop"
$env:Path = "C:\hadoop\bin;$env:Path"
```

Check:

```powershell
Test-Path C:\hadoop\bin\winutils.exe
```

### 5. Run Pipeline

```powershell
python .\scripts\run_pipeline.py
```

### 6. Run ML Workflow

```powershell
python .\scripts\run_ml.py
```

### 7. Start API

```powershell
python .\scripts\run_api.py
```

### 8. Start Docker API

```powershell
docker compose up -d
```

### 9. Validate Terraform Template

```powershell
python .\scripts\validate_terraform_template.py
```

---

## Useful Commands

### Run Data Quality Validation

```powershell
python .\scripts\validate_lakehouse.py
```

### Build dbt Analytics Layer

```powershell
python .\scripts\run_dbt.py
```

### Train ML Model

```powershell
python .\scripts\run_ml.py
```

### Start FastAPI

```powershell
python .\scripts\run_api.py
```

### Run Copilot Evaluation

```powershell
python .\scripts\evaluate_copilot.py
```

### Generate Monitoring Report

```powershell
python .\scripts\generate_monitoring_report.py
```

### Build Docker API

```powershell
docker compose build
```

### Run Docker API

```powershell
docker compose up -d
```

### Run API Smoke Test

```powershell
python .\scripts\smoke_test_api.py
```

### Validate Terraform Template

```powershell
python .\scripts\validate_terraform_template.py
```

---

## CI/CD

The repository includes GitHub Actions workflows for:

- Python CI
- Docker Build CI
- Terraform Validate CI

The Python CI validates the core project workflow.

The Docker Build workflow validates that the FastAPI service can be containerised successfully.

The Terraform Validate workflow validates the AWS infrastructure template without creating cloud resources.

---

## Portfolio Value

This project demonstrates:

### Data Engineering

- PySpark ETL
- Bronze/Silver/Gold lakehouse design
- Data validation
- Pipeline automation

### Analytics Engineering

- dbt staging and marts
- DuckDB analytics database
- SQL transformation layer
- dbt tests and docs

### Machine Learning

- Feature engineering
- Leakage-aware target design (see "Machine Learning: Exploitation-Likelihood
  Classifier" above for a worked example of catching and fixing a
  label-leakage bug, not just avoiding it from the start)
- Imbalanced binary classification (KEV exploitation likelihood)
- Evaluation beyond accuracy: ROC-AUC, average precision, majority-class
  baseline
- MLflow tracking

### Explainable AI

- Feature importance
- SHAP explainability
- Model interpretation

### AI Engineering

- Retrieval-based remediation copilot
- Local knowledge base
- Context-aware recommendation logic
- Safety-aware defensive responses

### Backend Engineering

- FastAPI service
- Swagger documentation
- REST API endpoints
- ML inference endpoint

### MLOps / Platform Engineering

- API monitoring
- Runtime logging
- Metrics endpoint
- Docker containerisation
- Docker Compose deployment
- Docker Build CI

### Cloud / DevOps

- AWS architecture design
- Terraform Infrastructure as Code
- ECS Fargate deployment template
- ECR container registry template
- S3 lakehouse storage template
- CloudWatch monitoring template
- Terraform validation CI

### Cybersecurity Analytics

- CVE prioritisation
- CISA KEV enrichment
- CVSS analysis
- CWE remediation guidance
- Defensive vulnerability management

---

## Limitations

Current limitations:

- The API uses local DuckDB and local model artifacts.
- Docker Compose mounts local `analytics/` and `models/` directories.
- The Terraform template is an architecture template and has not been applied to production AWS.
- The RAG copilot uses a local knowledge base rather than a production vector database.
- EPSS values may be missing depending on available source data.
- The exploitation-likelihood model predicts KEV membership, which is
  itself an imperfect and delayed proxy for real-world exploitation --
  a CVE can be actively exploited before CISA adds it to KEV, so the
  model's positive labels lag reality somewhat.
- The classifier does not use text features (e.g. CVE description, NLP on
  vendor advisories), which likely carry additional predictive signal
  beyond the structured CVSS/CWE fields currently used.
- NVD ingestion only pulls the last 30 days of published CVEs per run (see
  'Data Sources' above), so the committed Gold dataset spans a narrow date
  range rather than NVD's full history. Two concrete effects: (1) the
  `monthly_vulnerability_trends` output has too few distinct months to show
  a real trend, it is closer to a single snapshot than a time series; and
  (2) the already-low KEV positive rate is partly inflated by
  right-censoring -- most CVEs in the dataset were published too recently
  for CISA to have confirmed real-world exploitation yet, which is a
  different problem from "exploited CVEs are simply rare" and would need a
  longer NVD history (or an older, fixed publication-date cutoff) to
  measure separately.
- Current local deployment uses Docker Compose rather than a hosted cloud service.
- Only 15 of 11,506 CVEs in the current training set are known-exploited (0.13%). Cross-validated ROC-AUC (~0.79) shows the model separates known-exploited CVEs from the bulk of the dataset better than chance, but precision@10/20/50 come out at 0.0 in the current run -- the best-ranked known-exploited CVE lands around rank ~190 of 11,506, behind roughly 190 CRITICAL-severity, high-CVSS CVEs that were never exploited (see 'Current Model Metrics' above for the full breakdown). In plain terms: CVSS/CWE metadata alone can flag "this looks dangerous" but can't reliably pick out which of several similarly-dangerous-looking CVEs actually gets exploited -- that needs a behavioural signal like EPSS, which this project deliberately doesn't reuse as a feature. Treat this as a broad risk-scoring signal, not a precise top-N triage tool, and the F1-tuned decision threshold the API uses can shift meaningfully on the next retrain.
- The copilot's `mean_quality_score` (see 'Copilot Evaluation' above) checks that retrieval and CWE-mapping behaved the way they're designed to, not that the remediation advice is actually good guidance -- there's no human-graded or LLM-graded quality baseline yet.

---

## Future Improvements

Planned next steps:

- Push Docker image to ECR
- Add AWS deployment pipeline
- Add HTTPS with ACM
- Add API authentication
- Add production secrets management
- Add S3-backed artifact loading
- Add scheduled data refresh workflow
- Add production vector database for RAG
- Add more advanced LLM evaluation
- Add CloudWatch alarms

---
