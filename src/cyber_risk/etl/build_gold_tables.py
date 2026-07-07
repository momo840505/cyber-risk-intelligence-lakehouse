from pyspark.sql import DataFrame, Window
from pyspark.sql import functions as F

from cyber_risk.config import GOLD_DIR, SILVER_DIR
from cyber_risk.etl.spark_session import create_spark_session


def get_latest_epss(silver_epss: DataFrame) -> DataFrame:
    latest_window = Window.partitionBy("cve_id").orderBy(F.col("epss_date").desc_nulls_last())
    return (
        silver_epss
        .withColumn("row_number", F.row_number().over(latest_window))
        .where(F.col("row_number") == 1)
        .drop("row_number")
        .select("cve_id", "epss_date", "epss_score", "epss_percentile")
    )


def build_vulnerability_priority(silver_nvd: DataFrame, silver_kev: DataFrame, silver_epss: DataFrame) -> DataFrame:
    latest_epss = get_latest_epss(silver_epss)

    kev_features = (
        silver_kev
        .select(
            "cve_id",
            "vendor_project",
            "product",
            "vulnerability_name",
            "date_added",
            "due_date",
            "required_action",
            "known_ransomware_campaign_use",
        )
        .withColumn("is_known_exploited", F.lit(1))
    )

    priority = (
        silver_nvd
        .join(latest_epss, on="cve_id", how="left")
        .join(kev_features, on="cve_id", how="left")
        .withColumn("is_known_exploited", F.coalesce(F.col("is_known_exploited"), F.lit(0)))
        .withColumn("vendor", F.coalesce(F.col("vendor_project"), F.col("affected_vendor")))
        .withColumn("product_name", F.coalesce(F.col("product"), F.col("affected_product")))
        .withColumn("is_network_attack", F.when(F.col("attack_vector") == "NETWORK", 1).otherwise(0))
        .withColumn("requires_no_user_interaction", F.when(F.col("user_interaction") == "NONE", 1).otherwise(0))
        .withColumn(
            "requires_low_or_no_privilege",
            F.when(F.col("privileges_required").isin("NONE", "LOW"), 1).otherwise(0),
        )
        .withColumn(
            "risk_score",
            F.round(
                F.coalesce(F.col("cvss_base_score"), F.lit(0.0)) * 0.45
                + F.coalesce(F.col("epss_percentile"), F.lit(0.0)) * 10.0 * 0.25
                + F.col("is_known_exploited") * 2.00
                + F.col("is_network_attack") * 0.50
                + F.col("requires_no_user_interaction") * 0.40
                + F.col("requires_low_or_no_privilege") * 0.30,
                2,
            ),
        )
        .withColumn(
            "priority_level",
            F.when(F.col("risk_score") >= 8.0, "Critical")
            .when(F.col("risk_score") >= 6.0, "High")
            .when(F.col("risk_score") >= 4.0, "Medium")
            .otherwise("Low"),
        )
        .select(
            "cve_id",
            "published_date",
            "published_year",
            "published_month",
            "last_modified_date",
            "vulnerability_status",
            "description",
            "cwe_id",
            "vendor",
            "product_name",
            "cvss_version",
            "cvss_base_score",
            "cvss_base_severity",
            "cvss_vector_string",
            "attack_vector",
            "attack_complexity",
            "privileges_required",
            "user_interaction",
            "confidentiality_impact",
            "integrity_impact",
            "availability_impact",
            "epss_date",
            "epss_score",
            "epss_percentile",
            "is_known_exploited",
            "known_ransomware_campaign_use",
            "date_added",
            "due_date",
            "required_action",
            "risk_score",
            "priority_level",
            "reference_count",
            "affected_entry_count",
        )
    )

    return priority


def build_vendor_risk_summary(priority: DataFrame) -> DataFrame:
    return (
        priority
        .where(F.col("vendor").isNotNull())
        .groupBy("vendor", "product_name")
        .agg(
            F.countDistinct("cve_id").alias("total_vulnerabilities"),
            F.sum("is_known_exploited").alias("known_exploited_count"),
            F.avg("risk_score").alias("average_risk_score"),
            F.max("risk_score").alias("maximum_risk_score"),
            F.avg("epss_score").alias("average_epss_score"),
            F.sum(F.when(F.col("priority_level") == "Critical", 1).otherwise(0)).alias("critical_count"),
            F.sum(F.when(F.col("priority_level") == "High", 1).otherwise(0)).alias("high_count"),
        )
        .withColumn("average_risk_score", F.round("average_risk_score", 2))
        .withColumn("maximum_risk_score", F.round("maximum_risk_score", 2))
        .withColumn("average_epss_score", F.round("average_epss_score", 4))
        .orderBy(F.col("known_exploited_count").desc(), F.col("average_risk_score").desc())
    )


def build_monthly_vulnerability_trends(priority: DataFrame) -> DataFrame:
    return (
        priority
        .where(F.col("published_year").isNotNull())
        .groupBy("published_year", "published_month")
        .agg(
            F.countDistinct("cve_id").alias("total_cve_count"),
            F.sum("is_known_exploited").alias("known_exploited_count"),
            F.avg("cvss_base_score").alias("average_cvss_score"),
            F.avg("epss_score").alias("average_epss_score"),
            F.sum(F.when(F.col("priority_level") == "Critical", 1).otherwise(0)).alias("critical_count"),
            F.sum(F.when(F.col("priority_level") == "High", 1).otherwise(0)).alias("high_count"),
            F.sum(F.when(F.col("attack_vector") == "NETWORK", 1).otherwise(0)).alias("network_attack_vector_count"),
        )
        .withColumn("average_cvss_score", F.round("average_cvss_score", 2))
        .withColumn("average_epss_score", F.round("average_epss_score", 4))
        .orderBy("published_year", "published_month")
    )


def build_cwe_risk_summary(priority: DataFrame) -> DataFrame:
    return (
        priority
        .where(F.col("cwe_id").isNotNull())
        .groupBy("cwe_id")
        .agg(
            F.countDistinct("cve_id").alias("total_vulnerabilities"),
            F.sum("is_known_exploited").alias("known_exploited_count"),
            F.avg("risk_score").alias("average_risk_score"),
            F.max("risk_score").alias("maximum_risk_score"),
            F.avg("cvss_base_score").alias("average_cvss_score"),
            F.avg("epss_score").alias("average_epss_score"),
        )
        .withColumn("average_risk_score", F.round("average_risk_score", 2))
        .withColumn("maximum_risk_score", F.round("maximum_risk_score", 2))
        .withColumn("average_cvss_score", F.round("average_cvss_score", 2))
        .withColumn("average_epss_score", F.round("average_epss_score", 4))
        .orderBy(F.col("known_exploited_count").desc(), F.col("average_risk_score").desc())
    )


def write_dataframe(dataframe: DataFrame, output_path: str, partition_columns: list[str] | None = None) -> None:
    writer = dataframe.write.mode("overwrite")
    if partition_columns:
        writer = writer.partitionBy(*partition_columns)
    writer.parquet(output_path)


def print_summary(table_name: str, dataframe: DataFrame) -> None:
    print(f"\n========== {table_name} ==========")
    print(f"Rows: {dataframe.count():,}")
    dataframe.show(10, truncate=80)


def main() -> None:
    spark = create_spark_session("BuildGoldTables")

    try:
        silver_kev = spark.read.parquet(str(SILVER_DIR / "silver_kev"))
        silver_epss = spark.read.parquet(str(SILVER_DIR / "silver_epss"))
        silver_nvd = spark.read.parquet(str(SILVER_DIR / "silver_nvd"))

        vulnerability_priority = build_vulnerability_priority(silver_nvd, silver_kev, silver_epss)
        vendor_risk_summary = build_vendor_risk_summary(vulnerability_priority)
        monthly_vulnerability_trends = build_monthly_vulnerability_trends(vulnerability_priority)
        cwe_risk_summary = build_cwe_risk_summary(vulnerability_priority)

        write_dataframe(
            vulnerability_priority,
            str(GOLD_DIR / "vulnerability_priority"),
            partition_columns=["published_year", "published_month"],
        )
        write_dataframe(vendor_risk_summary, str(GOLD_DIR / "vendor_risk_summary"))
        write_dataframe(monthly_vulnerability_trends, str(GOLD_DIR / "monthly_vulnerability_trends"))
        write_dataframe(cwe_risk_summary, str(GOLD_DIR / "cwe_risk_summary"))

        print_summary("Gold Vulnerability Priority", vulnerability_priority)
        print_summary("Gold Vendor Risk Summary", vendor_risk_summary)
        print_summary("Gold Monthly Vulnerability Trends", monthly_vulnerability_trends)
        print_summary("Gold CWE Risk Summary", cwe_risk_summary)
        print("\nGold tables built successfully.")

    finally:
        spark.stop()


if __name__ == "__main__":
    main()
