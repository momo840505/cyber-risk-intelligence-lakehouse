from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st


# =========================
# Page configuration
# =========================

st.set_page_config(
    page_title="Cyber Risk Intelligence Dashboard",
    page_icon="🛡️",
    layout="wide",
)


# =========================
# Paths
# =========================

BASE_DIR = Path(__file__).resolve().parents[1]
GOLD_DIR = BASE_DIR / "data" / "gold"


# =========================
# Styling
# =========================

st.markdown(
    """
    <style>
    .main-title {
        font-size: 2.4rem;
        font-weight: 800;
        margin-bottom: 0.2rem;
    }

    .sub-title {
        font-size: 1.05rem;
        color: #6b7280;
        margin-bottom: 1.5rem;
    }

    .metric-card {
        background: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 18px;
        padding: 18px 20px;
        box-shadow: 0 4px 14px rgba(15, 23, 42, 0.06);
    }

    .metric-label {
        font-size: 0.85rem;
        color: #6b7280;
        margin-bottom: 0.4rem;
    }

    .metric-value {
        font-size: 1.9rem;
        font-weight: 800;
        color: #111827;
    }

    .section-header {
        font-size: 1.35rem;
        font-weight: 750;
        margin-top: 1.2rem;
        margin-bottom: 0.7rem;
    }

    .small-note {
        font-size: 0.85rem;
        color: #6b7280;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# =========================
# Helper functions
# =========================

@st.cache_data(show_spinner=False)
def load_gold_table(table_name: str) -> pd.DataFrame:
    table_path = GOLD_DIR / table_name

    if not table_path.exists():
        raise FileNotFoundError(
            f"Missing table: {table_path}. "
            "Please run the Silver and Gold ETL scripts first."
        )

    return pd.read_parquet(table_path)


def format_number(value) -> str:
    if pd.isna(value):
        return "0"
    return f"{int(value):,}"


def format_score(value) -> str:
    if pd.isna(value):
        return "N/A"
    return f"{float(value):.2f}"


def metric_card(label: str, value: str):
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def priority_sort_key(priority: str) -> int:
    priority_order = {
        "Critical": 1,
        "High": 2,
        "Medium": 3,
        "Low": 4,
        "Unknown": 99,
    }
    return priority_order.get(str(priority), 99)


def add_month_label(dataframe: pd.DataFrame) -> pd.DataFrame:
    dataframe = dataframe.copy()

    if {"published_year", "published_month"}.issubset(dataframe.columns):
        dataframe["month_label"] = (
            dataframe["published_year"].astype(str)
            + "-"
            + dataframe["published_month"].astype(str).str.zfill(2)
        )

    return dataframe


# =========================
# Load data
# =========================

try:
    vulnerability_priority = load_gold_table("vulnerability_priority")
    vendor_risk_summary = load_gold_table("vendor_risk_summary")
    monthly_vulnerability_trends = load_gold_table("monthly_vulnerability_trends")
    cwe_risk_summary = load_gold_table("cwe_risk_summary")

except FileNotFoundError as error:
    st.error(str(error))
    st.info(
        "Run these commands first:\n\n"
        "python -m cyber_risk.etl.build_silver_tables\n\n"
        "python -m cyber_risk.etl.build_gold_tables"
    )
    st.stop()


# =========================
# Basic cleaning for dashboard display
# =========================

vulnerability_priority = vulnerability_priority.copy()

if "priority_level" in vulnerability_priority.columns:
    vulnerability_priority["priority_level"] = vulnerability_priority["priority_level"].fillna("Unknown")

if "attack_vector" in vulnerability_priority.columns:
    vulnerability_priority["attack_vector_display"] = vulnerability_priority["attack_vector"].fillna("Unknown")
else:
    vulnerability_priority["attack_vector_display"] = "Unknown"

if "vendor" in vulnerability_priority.columns:
    vulnerability_priority["vendor"] = vulnerability_priority["vendor"].fillna("Unknown")

if "product_name" in vulnerability_priority.columns:
    vulnerability_priority["product_name"] = vulnerability_priority["product_name"].fillna("Unknown")


# =========================
# Header
# =========================

st.markdown(
    '<div class="main-title">🛡️ Cyber Risk Intelligence Dashboard</div>',
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="sub-title">
    Interactive dashboard for analysing CVE, CVSS, EPSS, and known exploited vulnerability intelligence.
    </div>
    """,
    unsafe_allow_html=True,
)

st.caption(
    "Data model: Gold vulnerability priority, vendor risk summary, monthly vulnerability trends, and CWE risk summary tables."
)


# =========================
# Sidebar filters
# =========================

st.sidebar.title("🔎 Filters")

available_priorities = sorted(
    vulnerability_priority["priority_level"].dropna().unique().tolist(),
    key=priority_sort_key,
)

selected_priorities = st.sidebar.multiselect(
    "Priority level",
    options=available_priorities,
    default=available_priorities,
)

available_attack_vectors = sorted(
    vulnerability_priority["attack_vector_display"].dropna().unique().tolist()
)

selected_attack_vectors = st.sidebar.multiselect(
    "Attack vector",
    options=available_attack_vectors,
    default=[],
    help="Leave empty to include all attack vectors.",
)

vendor_keyword = st.sidebar.text_input(
    "Vendor keyword",
    placeholder="Example: Microsoft, Cisco, Oracle",
)

known_exploited_only = st.sidebar.checkbox(
    "Show known exploited vulnerabilities only",
    value=False,
)

minimum_risk_score = st.sidebar.slider(
    "Minimum risk score",
    min_value=0.0,
    max_value=12.0,
    value=0.0,
    step=0.5,
)


# =========================
# Apply filters
# =========================

filtered_vulnerabilities = vulnerability_priority.copy()

if selected_priorities:
    filtered_vulnerabilities = filtered_vulnerabilities[
        filtered_vulnerabilities["priority_level"].isin(selected_priorities)
    ]

# Important:
# Only apply attack vector filter when the user actually selects something.
# This prevents NULL attack_vector rows from being excluded by default.
if selected_attack_vectors:
    filtered_vulnerabilities = filtered_vulnerabilities[
        filtered_vulnerabilities["attack_vector_display"].isin(selected_attack_vectors)
    ]

if vendor_keyword.strip():
    filtered_vulnerabilities = filtered_vulnerabilities[
        filtered_vulnerabilities["vendor"]
        .fillna("")
        .str.contains(vendor_keyword.strip(), case=False, na=False)
    ]

if known_exploited_only and "is_known_exploited" in filtered_vulnerabilities.columns:
    filtered_vulnerabilities = filtered_vulnerabilities[
        filtered_vulnerabilities["is_known_exploited"].fillna(0) == 1
    ]

if "risk_score" in filtered_vulnerabilities.columns:
    filtered_vulnerabilities = filtered_vulnerabilities[
        filtered_vulnerabilities["risk_score"].fillna(0) >= minimum_risk_score
    ]


# =========================
# KPI cards
# =========================

total_cves = len(filtered_vulnerabilities)

critical_count = filtered_vulnerabilities["priority_level"].eq("Critical").sum()
high_count = filtered_vulnerabilities["priority_level"].eq("High").sum()

known_exploited_count = (
    filtered_vulnerabilities["is_known_exploited"].fillna(0).sum()
    if "is_known_exploited" in filtered_vulnerabilities.columns
    else 0
)

average_risk_score = (
    filtered_vulnerabilities["risk_score"].mean()
    if "risk_score" in filtered_vulnerabilities.columns
    else None
)

st.markdown('<div class="section-header">Executive Summary</div>', unsafe_allow_html=True)

kpi_col_1, kpi_col_2, kpi_col_3, kpi_col_4, kpi_col_5 = st.columns(5)

with kpi_col_1:
    metric_card("Total CVEs", format_number(total_cves))

with kpi_col_2:
    metric_card("Critical", format_number(critical_count))

with kpi_col_3:
    metric_card("High", format_number(high_count))

with kpi_col_4:
    metric_card("Known Exploited", format_number(known_exploited_count))

with kpi_col_5:
    metric_card("Average Risk Score", format_score(average_risk_score))


# =========================
# Risk distribution charts
# =========================

st.markdown('<div class="section-header">Risk Distribution</div>', unsafe_allow_html=True)

chart_col_1, chart_col_2 = st.columns(2)

with chart_col_1:
    priority_distribution = (
        filtered_vulnerabilities["priority_level"]
        .fillna("Unknown")
        .value_counts()
        .reset_index()
    )
    priority_distribution.columns = ["priority_level", "count"]
    priority_distribution["sort_order"] = priority_distribution["priority_level"].apply(priority_sort_key)
    priority_distribution = priority_distribution.sort_values("sort_order")

    fig_priority = px.bar(
        priority_distribution,
        x="priority_level",
        y="count",
        title="Priority Distribution",
        text="count",
    )
    fig_priority.update_layout(
        xaxis_title="Priority Level",
        yaxis_title="Number of CVEs",
        height=420,
        margin=dict(l=20, r=20, t=60, b=40),
    )
    fig_priority.update_traces(textposition="outside")
    st.plotly_chart(fig_priority, use_container_width=True)

with chart_col_2:
    if "cvss_base_severity" in filtered_vulnerabilities.columns:
        severity_distribution = (
            filtered_vulnerabilities["cvss_base_severity"]
            .fillna("Unknown")
            .value_counts()
            .reset_index()
        )
        severity_distribution.columns = ["severity", "count"]

        fig_severity = px.pie(
            severity_distribution,
            names="severity",
            values="count",
            title="CVSS Severity Distribution",
            hole=0.45,
        )
        fig_severity.update_layout(
            height=420,
            margin=dict(l=20, r=20, t=60, b=40),
        )
        st.plotly_chart(fig_severity, use_container_width=True)


# =========================
# Trend and vendor analysis
# =========================

st.markdown('<div class="section-header">Trend and Vendor Analysis</div>', unsafe_allow_html=True)

trend_col, vendor_col = st.columns(2)

with trend_col:
    monthly_chart_data = add_month_label(monthly_vulnerability_trends)

    if {"month_label", "total_cve_count"}.issubset(monthly_chart_data.columns):
        monthly_chart_data = monthly_chart_data.sort_values(["published_year", "published_month"])

        fig_monthly = px.line(
            monthly_chart_data,
            x="month_label",
            y="total_cve_count",
            markers=True,
            title="Monthly Vulnerability Trends",
            text="total_cve_count",
        )
        fig_monthly.update_layout(
            xaxis_title="Month",
            yaxis_title="Total CVEs",
            height=420,
            margin=dict(l=20, r=20, t=60, b=40),
            xaxis_type="category",
        )
        fig_monthly.update_traces(textposition="top center")
        st.plotly_chart(fig_monthly, use_container_width=True)

with vendor_col:
    if {"vendor", "product_name", "maximum_risk_score"}.issubset(vendor_risk_summary.columns):
        top_vendor_risk = (
            vendor_risk_summary
            .dropna(subset=["vendor", "maximum_risk_score"])
            .sort_values("maximum_risk_score", ascending=False)
            .head(10)
            .copy()
        )

        top_vendor_risk["vendor_product"] = (
            top_vendor_risk["vendor"].fillna("Unknown").astype(str).str.slice(0, 22)
            + " - "
            + top_vendor_risk["product_name"].fillna("Unknown").astype(str).str.slice(0, 28)
        )

        fig_vendor = px.bar(
            top_vendor_risk.sort_values("maximum_risk_score"),
            x="maximum_risk_score",
            y="vendor_product",
            orientation="h",
            title="Top Vendor/Product Risk Ranking",
            text="maximum_risk_score",
        )
        fig_vendor.update_layout(
            xaxis_title="Maximum Risk Score",
            yaxis_title="Vendor / Product",
            height=420,
            margin=dict(l=20, r=20, t=60, b=40),
        )
        st.plotly_chart(fig_vendor, use_container_width=True)


# =========================
# CWE analysis
# =========================

st.markdown('<div class="section-header">CWE Weakness Risk Analysis</div>', unsafe_allow_html=True)

if {"cwe_id", "maximum_risk_score", "total_vulnerabilities"}.issubset(cwe_risk_summary.columns):
    top_cwe_risk = (
        cwe_risk_summary
        .dropna(subset=["cwe_id"])
        .sort_values(["maximum_risk_score", "total_vulnerabilities"], ascending=False)
        .head(15)
    )

    fig_cwe = px.bar(
        top_cwe_risk.sort_values("maximum_risk_score"),
        x="maximum_risk_score",
        y="cwe_id",
        orientation="h",
        title="Top CWE Categories by Maximum Risk Score",
        hover_data=["total_vulnerabilities", "known_exploited_count", "average_cvss_score"],
    )
    fig_cwe.update_layout(
        xaxis_title="Maximum Risk Score",
        yaxis_title="CWE ID",
        height=500,
        margin=dict(l=20, r=20, t=60, b=40),
    )
    st.plotly_chart(fig_cwe, use_container_width=True)


# =========================
# Top vulnerabilities table
# =========================

st.markdown('<div class="section-header">Top Priority Vulnerabilities</div>', unsafe_allow_html=True)

display_columns = [
    "cve_id",
    "vendor",
    "product_name",
    "cvss_base_score",
    "cvss_base_severity",
    "epss_score",
    "is_known_exploited",
    "risk_score",
    "priority_level",
    "attack_vector",
    "published_date",
]

available_display_columns = [
    column for column in display_columns if column in filtered_vulnerabilities.columns
]

if "risk_score" in filtered_vulnerabilities.columns:
    top_vulnerabilities = (
        filtered_vulnerabilities
        .sort_values("risk_score", ascending=False)
        .head(50)
        [available_display_columns]
    )
else:
    top_vulnerabilities = filtered_vulnerabilities.head(50)[available_display_columns]

st.dataframe(
    top_vulnerabilities,
    use_container_width=True,
    hide_index=True,
)

csv_data = top_vulnerabilities.to_csv(index=False).encode("utf-8")

st.download_button(
    label="⬇️ Download Top Vulnerabilities as CSV",
    data=csv_data,
    file_name="top_priority_vulnerabilities.csv",
    mime="text/csv",
)


# =========================
# Footer
# =========================

st.markdown("---")
st.markdown(
    """
    <div class="small-note">
    Built with Python, PySpark, Streamlit, and Plotly.
    Data source signals include CVE, CVSS, EPSS, and known exploited vulnerability intelligence.
    </div>
    """,
    unsafe_allow_html=True,
)