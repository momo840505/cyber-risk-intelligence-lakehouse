from pathlib import Path

import json

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

# This reads the small, git-committed snapshot in app/data/gold/ (single flat parquet
# files, one per Gold table) rather than the full local lakehouse at data/gold/ (PySpark
# output, gitignored). Streamlit Community Cloud only has this repo's committed files to
# work with -- see scripts/prepare_dashboard_data.py for how the snapshot is produced.
GOLD_DIR = BASE_DIR / "app" / "data" / "gold"
SNAPSHOT_METADATA_PATH = GOLD_DIR / "_snapshot_metadata.json"


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
    table_path = GOLD_DIR / f"{table_name}.parquet"

    if not table_path.exists():
        raise FileNotFoundError(
            f"Missing table: {table_path}. "
            "Run the pipeline (python .\\scripts\\run_pipeline.py), then "
            "python scripts\\prepare_dashboard_data.py to build the dashboard snapshot."
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
        "python .\\scripts\\run_pipeline.py\n\n"
        "python scripts\\prepare_dashboard_data.py"
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
    "Dashboard source: committed Gold snapshot generated from the PySpark Gold layer. "
    "Charts are recalculated from the filtered vulnerability-level snapshot."
)

if SNAPSHOT_METADATA_PATH.exists():
    try:
        snapshot_metadata = json.loads(
            SNAPSHOT_METADATA_PATH.read_text(encoding="utf-8")
        )
        generated_at = snapshot_metadata.get("generated_at_utc", "unknown")
        date_min = snapshot_metadata.get("published_date_min", "unknown")
        date_max = snapshot_metadata.get("published_date_max", "unknown")

        st.caption(
            f"Snapshot generated: {generated_at} | "
            f"CVE publication range: {date_min} to {date_max}"
        )
    except (OSError, ValueError, json.JSONDecodeError):
        pass


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
    required_trend_columns = {
        "published_year",
        "published_month",
    }

    if required_trend_columns.issubset(filtered_vulnerabilities.columns):
        monthly_chart_data = (
            filtered_vulnerabilities
            .dropna(subset=["published_year", "published_month"])
            .groupby(
                ["published_year", "published_month"],
                as_index=False,
            )
            .agg(
                total_cve_count=("cve_id", "count"),
                known_exploited_count=(
                    "is_known_exploited",
                    lambda series: int(series.fillna(0).sum()),
                ),
            )
            .sort_values(["published_year", "published_month"])
        )

        monthly_chart_data["published_year"] = (
            monthly_chart_data["published_year"].astype(int)
        )
        monthly_chart_data["published_month"] = (
            monthly_chart_data["published_month"].astype(int)
        )

        monthly_chart_data["month_label"] = (
            monthly_chart_data["published_year"].astype(str)
            + "-"
            + monthly_chart_data["published_month"].astype(str).str.zfill(2)
        )

        # The committed snapshot can start or end part-way through a calendar
        # month. Mark those boundary months explicitly so the chart is not
        # interpreted as a complete month-over-month comparison.
        if "published_date" in vulnerability_priority.columns:
            source_dates = pd.to_datetime(
                vulnerability_priority["published_date"],
                errors="coerce",
            ).dropna()

            if not source_dates.empty:
                first_source_date = source_dates.min()
                latest_source_date = source_dates.max()

                partial_periods = set()

                if first_source_date.day > 1:
                    partial_periods.add(
                        (int(first_source_date.year), int(first_source_date.month))
                    )

                latest_month_end = latest_source_date + pd.offsets.MonthEnd(0)

                if latest_source_date.normalize() < latest_month_end.normalize():
                    partial_periods.add(
                        (int(latest_source_date.year), int(latest_source_date.month))
                    )

                for partial_year, partial_month in sorted(partial_periods):
                    partial_mask = (
                        monthly_chart_data["published_year"].eq(partial_year)
                        & monthly_chart_data["published_month"].eq(partial_month)
                    )

                    monthly_chart_data.loc[
                        partial_mask,
                        "month_label",
                    ] = (
                        monthly_chart_data.loc[
                            partial_mask,
                            "month_label",
                        ]
                        + " (partial)"
                    )

        if not monthly_chart_data.empty:
            fig_monthly = px.line(
                monthly_chart_data,
                x="month_label",
                y="total_cve_count",
                markers=True,
                title="Monthly Vulnerability Trends",
                text="total_cve_count",
                hover_data={
                    "known_exploited_count": True,
                    "published_year": False,
                    "published_month": False,
                },
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
        else:
            st.info("No monthly trend data matches the current filters.")


with vendor_col:
    required_vendor_columns = {
        "vendor",
        "product_name",
        "risk_score",
    }

    if required_vendor_columns.issubset(filtered_vulnerabilities.columns):
        vendor_group_columns = ["vendor", "product_name"]

        vendor_agg = {
            "total_vulnerabilities": ("cve_id", "count"),
            "average_risk_score": ("risk_score", "mean"),
            "maximum_risk_score": ("risk_score", "max"),
        }

        if "is_known_exploited" in filtered_vulnerabilities.columns:
            vendor_agg["known_exploited_count"] = (
                "is_known_exploited",
                lambda series: int(series.fillna(0).sum()),
            )

        vendor_chart_data = (
            filtered_vulnerabilities
            .dropna(subset=["vendor", "product_name"])
            .groupby(vendor_group_columns, as_index=False)
            .agg(**vendor_agg)
        )

        vendor_chart_data = vendor_chart_data[
            vendor_chart_data["vendor"].astype(str).str.strip().ne("")
            & vendor_chart_data["product_name"].astype(str).str.strip().ne("")
        ].copy()

        if "known_exploited_count" not in vendor_chart_data.columns:
            vendor_chart_data["known_exploited_count"] = 0

        if (
            not vendor_chart_data.empty
            and vendor_chart_data["known_exploited_count"].sum() > 0
        ):
            vendor_metric = "known_exploited_count"
            vendor_title = "Top Vendor/Product by Known Exploited Vulnerabilities"
            vendor_axis_title = "Known Exploited Vulnerabilities"
            vendor_text_format = None

            top_vendor_risk = (
                vendor_chart_data
                .sort_values(
                    [
                        "known_exploited_count",
                        "average_risk_score",
                        "total_vulnerabilities",
                    ],
                    ascending=[False, False, False],
                )
                .head(10)
                .copy()
            )
        else:
            # If the active filters contain no KEV matches, fall back to
            # average risk instead of rendering ten identical zero-length bars.
            vendor_metric = "average_risk_score"
            vendor_title = "Top Vendor/Product by Average Risk Score"
            vendor_axis_title = "Average Risk Score"
            vendor_text_format = ".2f"

            top_vendor_risk = (
                vendor_chart_data
                .sort_values(
                    [
                        "average_risk_score",
                        "total_vulnerabilities",
                    ],
                    ascending=[False, False],
                )
                .head(10)
                .copy()
            )

        if not top_vendor_risk.empty:
            top_vendor_risk["vendor_product"] = (
                top_vendor_risk["vendor"]
                .fillna("Unknown")
                .astype(str)
                .str.slice(0, 22)
                + " - "
                + top_vendor_risk["product_name"]
                .fillna("Unknown")
                .astype(str)
                .str.slice(0, 28)
            )

            vendor_plot_data = top_vendor_risk.sort_values(vendor_metric)

            fig_vendor = px.bar(
                vendor_plot_data,
                x=vendor_metric,
                y="vendor_product",
                orientation="h",
                title=vendor_title,
                text=vendor_metric,
                hover_data={
                    "known_exploited_count": True,
                    "total_vulnerabilities": ":,",
                    "average_risk_score": ":.2f",
                    "maximum_risk_score": ":.2f",
                },
            )

            if vendor_text_format:
                fig_vendor.update_traces(
                    texttemplate=f"%{{text:{vendor_text_format}}}",
                    textposition="outside",
                )
            else:
                fig_vendor.update_traces(textposition="outside")

            fig_vendor.update_layout(
                xaxis_title=vendor_axis_title,
                yaxis_title="Vendor / Product",
                height=420,
                margin=dict(l=20, r=35, t=60, b=40),
            )

            st.plotly_chart(fig_vendor, use_container_width=True)
        else:
            st.info("No vendor/product data matches the current filters.")


# =========================
# CWE analysis
# =========================

st.markdown('<div class="section-header">CWE Weakness Risk Analysis</div>', unsafe_allow_html=True)

required_cwe_columns = {
    "cwe_id",
    "risk_score",
}

if required_cwe_columns.issubset(filtered_vulnerabilities.columns):
    cwe_agg = {
        "total_vulnerabilities": ("cve_id", "count"),
        "average_risk_score": ("risk_score", "mean"),
        "maximum_risk_score": ("risk_score", "max"),
    }

    if "is_known_exploited" in filtered_vulnerabilities.columns:
        cwe_agg["known_exploited_count"] = (
            "is_known_exploited",
            lambda series: int(series.fillna(0).sum()),
        )

    if "cvss_base_score" in filtered_vulnerabilities.columns:
        cwe_agg["average_cvss_score"] = (
            "cvss_base_score",
            "mean",
        )

    if "epss_score" in filtered_vulnerabilities.columns:
        cwe_agg["average_epss_score"] = (
            "epss_score",
            "mean",
        )

    cwe_chart_data = (
        filtered_vulnerabilities
        .dropna(subset=["cwe_id"])
        .groupby("cwe_id", as_index=False)
        .agg(**cwe_agg)
    )

    cwe_chart_data = cwe_chart_data[
        cwe_chart_data["cwe_id"].astype(str).str.strip().ne("")
        & cwe_chart_data["cwe_id"].astype(str).ne("NVD-CWE-noinfo")
    ].copy()

    if "known_exploited_count" not in cwe_chart_data.columns:
        cwe_chart_data["known_exploited_count"] = 0

    if "average_cvss_score" not in cwe_chart_data.columns:
        cwe_chart_data["average_cvss_score"] = float("nan")

    if "average_epss_score" not in cwe_chart_data.columns:
        cwe_chart_data["average_epss_score"] = float("nan")

    if (
        not cwe_chart_data.empty
        and cwe_chart_data["known_exploited_count"].sum() > 0
    ):
        cwe_metric = "known_exploited_count"
        cwe_title = "Top CWE Categories by Known Exploited Vulnerabilities"
        cwe_axis_title = "Known Exploited Vulnerabilities"
        cwe_text_format = None

        top_cwe_risk = (
            cwe_chart_data
            .sort_values(
                [
                    "known_exploited_count",
                    "average_risk_score",
                    "total_vulnerabilities",
                ],
                ascending=[False, False, False],
            )
            .head(15)
            .copy()
        )
    else:
        # When the current filter has no known exploited CVEs, average risk
        # remains informative and avoids an all-zero ranking.
        cwe_metric = "average_risk_score"
        cwe_title = "Top CWE Categories by Average Risk Score"
        cwe_axis_title = "Average Risk Score"
        cwe_text_format = ".2f"

        top_cwe_risk = (
            cwe_chart_data
            .sort_values(
                [
                    "average_risk_score",
                    "total_vulnerabilities",
                ],
                ascending=[False, False],
            )
            .head(15)
            .copy()
        )

    if not top_cwe_risk.empty:
        cwe_plot_data = top_cwe_risk.sort_values(cwe_metric)

        fig_cwe = px.bar(
            cwe_plot_data,
            x=cwe_metric,
            y="cwe_id",
            orientation="h",
            title=cwe_title,
            text=cwe_metric,
            hover_data={
                "known_exploited_count": True,
                "total_vulnerabilities": ":,",
                "average_risk_score": ":.2f",
                "maximum_risk_score": ":.2f",
                "average_cvss_score": ":.2f",
                "average_epss_score": ":.4f",
            },
        )

        if cwe_text_format:
            fig_cwe.update_traces(
                texttemplate=f"%{{text:{cwe_text_format}}}",
                textposition="outside",
            )
        else:
            fig_cwe.update_traces(textposition="outside")

        fig_cwe.update_layout(
            xaxis_title=cwe_axis_title,
            yaxis_title="CWE ID",
            height=500,
            margin=dict(l=20, r=35, t=60, b=40),
        )

        st.plotly_chart(fig_cwe, use_container_width=True)
    else:
        st.info("No CWE data matches the current filters.")


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