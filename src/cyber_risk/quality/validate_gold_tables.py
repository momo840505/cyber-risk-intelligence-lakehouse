from pathlib import Path
from typing import List

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[3]
GOLD_DIR = BASE_DIR / "data" / "gold"
REPORTS_DIR = BASE_DIR / "reports"
REPORT_PATH = REPORTS_DIR / "data_quality_report.csv"


class ValidationResult:
    def __init__(self, status: str, check_name: str, message: str):
        self.status = status
        self.check_name = check_name
        self.message = message

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "check_name": self.check_name,
            "message": self.message,
        }


def pass_check(check_name: str, message: str) -> ValidationResult:
    return ValidationResult("PASS", check_name, message)


def warn_check(check_name: str, message: str) -> ValidationResult:
    return ValidationResult("WARN", check_name, message)


def fail_check(check_name: str, message: str) -> ValidationResult:
    return ValidationResult("FAIL", check_name, message)


def load_gold_table(table_name: str) -> pd.DataFrame:
    table_path = GOLD_DIR / table_name

    if not table_path.exists():
        raise FileNotFoundError(f"Missing Gold table: {table_path}")

    return pd.read_parquet(table_path)


def check_required_columns(
    dataframe: pd.DataFrame,
    table_name: str,
    required_columns: List[str],
) -> List[ValidationResult]:
    results = []

    missing_columns = [
        column for column in required_columns if column not in dataframe.columns
    ]

    if missing_columns:
        results.append(
            fail_check(
                f"{table_name} required columns",
                f"Missing columns: {missing_columns}",
            )
        )
    else:
        results.append(
            pass_check(
                f"{table_name} required columns",
                "All required columns are present.",
            )
        )

    return results


def check_non_empty_table(dataframe: pd.DataFrame, table_name: str) -> List[ValidationResult]:
    if len(dataframe) == 0:
        return [
            fail_check(
                f"{table_name} row count",
                "Table is empty.",
            )
        ]

    return [
        pass_check(
            f"{table_name} row count",
            f"Table contains {len(dataframe):,} rows.",
        )
    ]


def validate_vulnerability_priority(dataframe: pd.DataFrame) -> List[ValidationResult]:
    table_name = "vulnerability_priority"

    results = []
    results.extend(check_non_empty_table(dataframe, table_name))

    required_columns = [
        "cve_id",
        "vendor",
        "product_name",
        "cvss_base_score",
        "cvss_base_severity",
        "epss_score",
        "is_known_exploited",
        "risk_score",
        "priority_level",
        "published_date",
    ]

    results.extend(check_required_columns(dataframe, table_name, required_columns))

    if "cve_id" in dataframe.columns:
        missing_cve_count = dataframe["cve_id"].isna().sum()

        if missing_cve_count > 0:
            results.append(
                fail_check(
                    "vulnerability_priority missing CVE IDs",
                    f"Found {missing_cve_count:,} rows with missing cve_id.",
                )
            )
        else:
            results.append(
                pass_check(
                    "vulnerability_priority missing CVE IDs",
                    "No missing cve_id values found.",
                )
            )

        duplicate_cve_count = dataframe["cve_id"].duplicated().sum()

        if duplicate_cve_count > 0:
            results.append(
                warn_check(
                    "vulnerability_priority duplicate CVE IDs",
                    f"Found {duplicate_cve_count:,} duplicate cve_id values.",
                )
            )
        else:
            results.append(
                pass_check(
                    "vulnerability_priority duplicate CVE IDs",
                    "No duplicate cve_id values found.",
                )
            )

    if "cvss_base_score" in dataframe.columns:
        valid_cvss = dataframe["cvss_base_score"].dropna().between(0, 10)

        if valid_cvss.all():
            results.append(
                pass_check(
                    "CVSS score range",
                    "All non-null CVSS scores are between 0 and 10.",
                )
            )
        else:
            invalid_count = (~valid_cvss).sum()
            results.append(
                fail_check(
                    "CVSS score range",
                    f"Found {invalid_count:,} invalid CVSS scores.",
                )
            )

    if "epss_score" in dataframe.columns:
        valid_epss = dataframe["epss_score"].dropna().between(0, 1)

        if valid_epss.all():
            results.append(
                pass_check(
                    "EPSS score range",
                    "All non-null EPSS scores are between 0 and 1.",
                )
            )
        else:
            invalid_count = (~valid_epss).sum()
            results.append(
                fail_check(
                    "EPSS score range",
                    f"Found {invalid_count:,} invalid EPSS scores.",
                )
            )

    if "risk_score" in dataframe.columns:
        valid_risk_score = dataframe["risk_score"].dropna().between(0, 12)

        if valid_risk_score.all():
            results.append(
                pass_check(
                    "Risk score range",
                    "All non-null risk scores are between 0 and 12.",
                )
            )
        else:
            invalid_count = (~valid_risk_score).sum()
            results.append(
                fail_check(
                    "Risk score range",
                    f"Found {invalid_count:,} invalid risk scores.",
                )
            )

    if "priority_level" in dataframe.columns:
        allowed_priorities = {"Critical", "High", "Medium", "Low"}
        actual_priorities = set(dataframe["priority_level"].dropna().unique())
        unexpected_priorities = sorted(actual_priorities - allowed_priorities)

        if unexpected_priorities:
            results.append(
                fail_check(
                    "Priority level values",
                    f"Unexpected priority levels: {unexpected_priorities}",
                )
            )
        else:
            results.append(
                pass_check(
                    "Priority level values",
                    "Priority levels are valid.",
                )
            )

    if "is_known_exploited" in dataframe.columns:
        allowed_flags = {0, 1}
        actual_flags = set(dataframe["is_known_exploited"].dropna().unique())
        unexpected_flags = sorted(actual_flags - allowed_flags)

        if unexpected_flags:
            results.append(
                fail_check(
                    "Known exploited flag values",
                    f"Unexpected values: {unexpected_flags}",
                )
            )
        else:
            results.append(
                pass_check(
                    "Known exploited flag values",
                    "Known exploited values are valid 0/1 flags.",
                )
            )

    return results


def validate_vendor_risk_summary(dataframe: pd.DataFrame) -> List[ValidationResult]:
    table_name = "vendor_risk_summary"

    results = []
    results.extend(check_non_empty_table(dataframe, table_name))

    required_columns = [
        "vendor",
        "product_name",
        "total_vulnerabilities",
        "known_exploited_count",
        "average_risk_score",
        "maximum_risk_score",
        "critical_count",
        "high_count",
    ]

    results.extend(check_required_columns(dataframe, table_name, required_columns))

    if "total_vulnerabilities" in dataframe.columns:
        invalid_count = (dataframe["total_vulnerabilities"].fillna(0) <= 0).sum()

        if invalid_count > 0:
            results.append(
                fail_check(
                    "Vendor total vulnerability count",
                    f"Found {invalid_count:,} vendors/products with invalid total_vulnerabilities.",
                )
            )
        else:
            results.append(
                pass_check(
                    "Vendor total vulnerability count",
                    "All vendor/product rows have positive vulnerability counts.",
                )
            )

    return results


def validate_monthly_trends(dataframe: pd.DataFrame) -> List[ValidationResult]:
    table_name = "monthly_vulnerability_trends"

    results = []
    results.extend(check_non_empty_table(dataframe, table_name))

    required_columns = [
        "published_year",
        "published_month",
        "total_cve_count",
        "known_exploited_count",
        "average_cvss_score",
        "critical_count",
        "high_count",
        "network_attack_vector_count",
    ]

    results.extend(check_required_columns(dataframe, table_name, required_columns))

    if "published_month" in dataframe.columns:
        valid_months = dataframe["published_month"].dropna().between(1, 12)

        if valid_months.all():
            results.append(
                pass_check(
                    "Monthly trend month values",
                    "All month values are between 1 and 12.",
                )
            )
        else:
            invalid_count = (~valid_months).sum()
            results.append(
                fail_check(
                    "Monthly trend month values",
                    f"Found {invalid_count:,} invalid month values.",
                )
            )

    return results


def validate_cwe_risk_summary(dataframe: pd.DataFrame) -> List[ValidationResult]:
    table_name = "cwe_risk_summary"

    results = []
    results.extend(check_non_empty_table(dataframe, table_name))

    required_columns = [
        "cwe_id",
        "total_vulnerabilities",
        "known_exploited_count",
        "average_risk_score",
        "maximum_risk_score",
        "average_cvss_score",
        "average_epss_score",
    ]

    results.extend(check_required_columns(dataframe, table_name, required_columns))

    if "cwe_id" in dataframe.columns:
        missing_cwe_count = dataframe["cwe_id"].isna().sum()

        if missing_cwe_count > 0:
            results.append(
                warn_check(
                    "CWE missing values",
                    f"Found {missing_cwe_count:,} rows with missing cwe_id.",
                )
            )
        else:
            results.append(
                pass_check(
                    "CWE missing values",
                    "No missing cwe_id values found.",
                )
            )

    return results


def print_results(results: List[ValidationResult]) -> None:
    print("\n========== Lakehouse Data Quality Report ==========\n")

    for result in results:
        print(f"[{result.status}] {result.check_name}")
        print(f"      {result.message}")

    pass_count = sum(result.status == "PASS" for result in results)
    warn_count = sum(result.status == "WARN" for result in results)
    fail_count = sum(result.status == "FAIL" for result in results)

    print("\n========== Summary ==========")
    print(f"PASS: {pass_count}")
    print(f"WARN: {warn_count}")
    print(f"FAIL: {fail_count}")

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report_dataframe = pd.DataFrame(
        [result.to_dict() for result in results]
    )

    report_dataframe.to_csv(REPORT_PATH, index=False)

    print(f"\nReport written to: {REPORT_PATH}")


    if fail_count == 0:
        print("\nData quality validation completed successfully.")
    else:
        print("\nData quality validation failed. Please review the failed checks.")


def main() -> None:
    all_results = []

    try:
        vulnerability_priority = load_gold_table("vulnerability_priority")
        vendor_risk_summary = load_gold_table("vendor_risk_summary")
        monthly_vulnerability_trends = load_gold_table("monthly_vulnerability_trends")
        cwe_risk_summary = load_gold_table("cwe_risk_summary")

    except FileNotFoundError as error:
        print(f"[FAIL] {error}")
        raise SystemExit(1)

    all_results.extend(validate_vulnerability_priority(vulnerability_priority))
    all_results.extend(validate_vendor_risk_summary(vendor_risk_summary))
    all_results.extend(validate_monthly_trends(monthly_vulnerability_trends))
    all_results.extend(validate_cwe_risk_summary(cwe_risk_summary))

    print_results(all_results)

    has_failure = any(result.status == "FAIL" for result in all_results)

    if has_failure:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
