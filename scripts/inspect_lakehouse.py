from pathlib import Path

from pyspark.sql import functions as F

from cyber_risk.config import GOLD_DIR, SILVER_DIR
from cyber_risk.etl.spark_session import create_spark_session


def inspect_table(spark, table_name: str, table_path: Path) -> None:
    if not table_path.exists():
        print(f"Missing table: {table_name} -> {table_path}")
        return

    dataframe = spark.read.parquet(str(table_path))
    print(f"\n========== {table_name} ==========")
    print(f"Rows: {dataframe.count():,}")
    print(f"Columns: {len(dataframe.columns)}")
    dataframe.printSchema()
    dataframe.show(10, truncate=80)


def main() -> None:
    spark = create_spark_session("InspectLakehouse")

    try:
        inspect_table(spark, "Silver KEV", SILVER_DIR / "silver_kev")
        inspect_table(spark, "Silver EPSS", SILVER_DIR / "silver_epss")
        inspect_table(spark, "Silver NVD", SILVER_DIR / "silver_nvd")
        inspect_table(spark, "Gold Vulnerability Priority", GOLD_DIR / "vulnerability_priority")
        inspect_table(spark, "Gold Vendor Risk Summary", GOLD_DIR / "vendor_risk_summary")
        inspect_table(spark, "Gold Monthly Trends", GOLD_DIR / "monthly_vulnerability_trends")
        inspect_table(spark, "Gold CWE Risk Summary", GOLD_DIR / "cwe_risk_summary")

        priority_path = GOLD_DIR / "vulnerability_priority"
        if priority_path.exists():
            priority = spark.read.parquet(str(priority_path))
            print("\n========== Top priority vulnerabilities ==========")
            (
                priority
                .select(
                    "cve_id",
                    "cvss_base_score",
                    "epss_score",
                    "is_known_exploited",
                    "risk_score",
                    "priority_level",
                    "vendor",
                    "product_name",
                )
                .orderBy(F.col("risk_score").desc())
                .show(20, truncate=80)
            )

            print("\n========== Priority distribution ==========")
            priority.groupBy("priority_level").count().orderBy(F.col("count").desc()).show()

    finally:
        spark.stop()


if __name__ == "__main__":
    main()
