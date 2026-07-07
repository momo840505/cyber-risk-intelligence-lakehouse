from pyspark.sql import DataFrame
from pyspark.sql import functions as F
from pyspark.sql.types import ArrayType, StructType

from cyber_risk.config import EPSS_BRONZE_DIR, KEV_BRONZE_DIR, NVD_BRONZE_DIR, SILVER_DIR
from cyber_risk.etl.spark_session import create_spark_session


def has_nested_field(schema, dotted_path: str) -> bool:
    """Return True when a nested Spark field exists in the inferred schema."""
    current_type = schema

    for field_name in dotted_path.split("."):
        if isinstance(current_type, StructType):
            matched_field = next(
                (field for field in current_type.fields if field.name == field_name),
                None,
            )
            if matched_field is None:
                return False
            current_type = matched_field.dataType

        elif isinstance(current_type, ArrayType):
            current_type = current_type.elementType
            if not isinstance(current_type, StructType):
                return False
            matched_field = next(
                (field for field in current_type.fields if field.name == field_name),
                None,
            )
            if matched_field is None:
                return False
            current_type = matched_field.dataType

        else:
            return False

    return True


def safe_array_item_field(
    dataframe: DataFrame,
    array_path: str,
    field_path: str,
    cast_type: str = "string",
):
    """Safely read the first item of an array field, otherwise return null."""
    if not has_nested_field(dataframe.schema, array_path):
        return F.lit(None).cast(cast_type)

    expression = F.col(array_path)[0]
    for field_name in field_path.split("."):
        expression = expression.getField(field_name)

    return expression.cast(cast_type)


def safe_english_array_value(dataframe: DataFrame, array_path: str):
    """Extract the English text value from arrays like descriptions[]."""
    if not has_nested_field(dataframe.schema, array_path):
        return F.lit(None).cast("string")

    return F.expr(f"filter({array_path}, item -> item.lang = 'en')[0].value")


def safe_array_size(dataframe: DataFrame, array_path: str):
    if not has_nested_field(dataframe.schema, array_path):
        return F.lit(0)
    return F.size(F.col(array_path))


def build_silver_kev(spark) -> DataFrame:
    input_path = str(KEV_BRONZE_DIR / "known_exploited_vulnerabilities.jsonl")
    kev_dataframe = spark.read.json(input_path)

    silver_kev = (
        kev_dataframe
        .select(
            F.col("cveID").alias("cve_id"),
            F.col("vendorProject").alias("vendor_project"),
            F.col("product").alias("product"),
            F.col("vulnerabilityName").alias("vulnerability_name"),
            F.to_date("dateAdded").alias("date_added"),
            F.to_date("dueDate").alias("due_date"),
            F.col("knownRansomwareCampaignUse").alias("known_ransomware_campaign_use"),
            F.col("requiredAction").alias("required_action"),
            F.col("shortDescription").alias("short_description"),
            F.col("notes").alias("notes"),
            F.concat_ws(", ", F.col("cwes")).alias("cwe_list"),
        )
        .where(F.col("cve_id").isNotNull())
        .dropDuplicates(["cve_id"])
        .withColumn("date_added_year", F.year("date_added"))
        .withColumn("date_added_month", F.month("date_added"))
    )

    return silver_kev


def build_silver_epss(spark) -> DataFrame:
    input_path = str(EPSS_BRONZE_DIR / "epss_top_scores.jsonl")
    epss_dataframe = spark.read.json(input_path)

    silver_epss = (
        epss_dataframe
        .select(
            F.col("cve").alias("cve_id"),
            F.col("epss").cast("double").alias("epss_score"),
            F.col("percentile").cast("double").alias("epss_percentile"),
            F.to_date("date").alias("epss_date"),
        )
        .where(F.col("cve_id").isNotNull())
        .where(F.col("epss_score").isNotNull())
        .dropDuplicates(["cve_id", "epss_date"])
        .withColumn("epss_year", F.year("epss_date"))
        .withColumn("epss_month", F.month("epss_date"))
    )

    return silver_epss


def build_silver_nvd(spark) -> DataFrame:
    input_path = str(NVD_BRONZE_DIR / "nvd_recent_cves.jsonl")
    nvd_dataframe = spark.read.json(input_path)

    english_description = safe_english_array_value(nvd_dataframe, "cve.descriptions")

    cwe_value = (
        F.expr("filter(cve.weaknesses[0].description, item -> item.lang = 'en')[0].value")
        if has_nested_field(nvd_dataframe.schema, "cve.weaknesses")
        else F.lit(None).cast("string")
    )

    cvss_v40_score = safe_array_item_field(
        nvd_dataframe, "cve.metrics.cvssMetricV40", "cvssData.baseScore", "double"
    )
    cvss_v31_score = safe_array_item_field(
        nvd_dataframe, "cve.metrics.cvssMetricV31", "cvssData.baseScore", "double"
    )
    cvss_v30_score = safe_array_item_field(
        nvd_dataframe, "cve.metrics.cvssMetricV30", "cvssData.baseScore", "double"
    )
    cvss_v2_score = safe_array_item_field(
        nvd_dataframe, "cve.metrics.cvssMetricV2", "cvssData.baseScore", "double"
    )

    silver_nvd = (
        nvd_dataframe
        .select(
            F.col("cve.id").alias("cve_id"),
            F.col("cve.sourceIdentifier").alias("source_identifier"),
            F.to_timestamp("cve.published").alias("published_datetime"),
            F.to_timestamp("cve.lastModified").alias("last_modified_datetime"),
            F.col("cve.vulnStatus").alias("vulnerability_status"),
            english_description.alias("description"),
            cwe_value.alias("cwe_id"),
            F.expr("cve.affected[0].affectedData[0].vendor").alias("affected_vendor"),
            F.expr("cve.affected[0].affectedData[0].product").alias("affected_product"),
            safe_array_size(nvd_dataframe, "cve.affected").alias("affected_entry_count"),
            safe_array_size(nvd_dataframe, "cve.references").alias("reference_count"),
            F.when(cvss_v40_score.isNotNull(), F.lit("4.0"))
            .when(cvss_v31_score.isNotNull(), F.lit("3.1"))
            .when(cvss_v30_score.isNotNull(), F.lit("3.0"))
            .when(cvss_v2_score.isNotNull(), F.lit("2.0"))
            .otherwise(F.lit(None))
            .alias("cvss_version"),
            F.coalesce(cvss_v40_score, cvss_v31_score, cvss_v30_score, cvss_v2_score)
            .alias("cvss_base_score"),
            F.coalesce(
                safe_array_item_field(nvd_dataframe, "cve.metrics.cvssMetricV40", "cvssData.baseSeverity"),
                safe_array_item_field(nvd_dataframe, "cve.metrics.cvssMetricV31", "cvssData.baseSeverity"),
                safe_array_item_field(nvd_dataframe, "cve.metrics.cvssMetricV30", "cvssData.baseSeverity"),
                safe_array_item_field(nvd_dataframe, "cve.metrics.cvssMetricV2", "baseSeverity"),
            ).alias("cvss_base_severity"),
            F.coalesce(
                safe_array_item_field(nvd_dataframe, "cve.metrics.cvssMetricV40", "cvssData.vectorString"),
                safe_array_item_field(nvd_dataframe, "cve.metrics.cvssMetricV31", "cvssData.vectorString"),
                safe_array_item_field(nvd_dataframe, "cve.metrics.cvssMetricV30", "cvssData.vectorString"),
                safe_array_item_field(nvd_dataframe, "cve.metrics.cvssMetricV2", "cvssData.vectorString"),
            ).alias("cvss_vector_string"),
            F.coalesce(
                safe_array_item_field(nvd_dataframe, "cve.metrics.cvssMetricV40", "cvssData.attackVector"),
                safe_array_item_field(nvd_dataframe, "cve.metrics.cvssMetricV31", "cvssData.attackVector"),
                safe_array_item_field(nvd_dataframe, "cve.metrics.cvssMetricV30", "cvssData.attackVector"),
                safe_array_item_field(nvd_dataframe, "cve.metrics.cvssMetricV2", "cvssData.accessVector"),
            ).alias("attack_vector"),
            F.coalesce(
                safe_array_item_field(nvd_dataframe, "cve.metrics.cvssMetricV40", "cvssData.attackComplexity"),
                safe_array_item_field(nvd_dataframe, "cve.metrics.cvssMetricV31", "cvssData.attackComplexity"),
                safe_array_item_field(nvd_dataframe, "cve.metrics.cvssMetricV30", "cvssData.attackComplexity"),
                safe_array_item_field(nvd_dataframe, "cve.metrics.cvssMetricV2", "cvssData.accessComplexity"),
            ).alias("attack_complexity"),
            F.coalesce(
                safe_array_item_field(nvd_dataframe, "cve.metrics.cvssMetricV40", "cvssData.privilegesRequired"),
                safe_array_item_field(nvd_dataframe, "cve.metrics.cvssMetricV31", "cvssData.privilegesRequired"),
                safe_array_item_field(nvd_dataframe, "cve.metrics.cvssMetricV30", "cvssData.privilegesRequired"),
            ).alias("privileges_required"),
            F.coalesce(
                safe_array_item_field(nvd_dataframe, "cve.metrics.cvssMetricV40", "cvssData.userInteraction"),
                safe_array_item_field(nvd_dataframe, "cve.metrics.cvssMetricV31", "cvssData.userInteraction"),
                safe_array_item_field(nvd_dataframe, "cve.metrics.cvssMetricV30", "cvssData.userInteraction"),
            ).alias("user_interaction"),
            F.coalesce(
                safe_array_item_field(nvd_dataframe, "cve.metrics.cvssMetricV40", "cvssData.vulnConfidentialityImpact"),
                safe_array_item_field(nvd_dataframe, "cve.metrics.cvssMetricV31", "cvssData.confidentialityImpact"),
                safe_array_item_field(nvd_dataframe, "cve.metrics.cvssMetricV30", "cvssData.confidentialityImpact"),
                safe_array_item_field(nvd_dataframe, "cve.metrics.cvssMetricV2", "cvssData.confidentialityImpact"),
            ).alias("confidentiality_impact"),
            F.coalesce(
                safe_array_item_field(nvd_dataframe, "cve.metrics.cvssMetricV40", "cvssData.vulnIntegrityImpact"),
                safe_array_item_field(nvd_dataframe, "cve.metrics.cvssMetricV31", "cvssData.integrityImpact"),
                safe_array_item_field(nvd_dataframe, "cve.metrics.cvssMetricV30", "cvssData.integrityImpact"),
                safe_array_item_field(nvd_dataframe, "cve.metrics.cvssMetricV2", "cvssData.integrityImpact"),
            ).alias("integrity_impact"),
            F.coalesce(
                safe_array_item_field(nvd_dataframe, "cve.metrics.cvssMetricV40", "cvssData.vulnAvailabilityImpact"),
                safe_array_item_field(nvd_dataframe, "cve.metrics.cvssMetricV31", "cvssData.availabilityImpact"),
                safe_array_item_field(nvd_dataframe, "cve.metrics.cvssMetricV30", "cvssData.availabilityImpact"),
                safe_array_item_field(nvd_dataframe, "cve.metrics.cvssMetricV2", "cvssData.availabilityImpact"),
            ).alias("availability_impact"),
        )
        .where(F.col("cve_id").isNotNull())
        .dropDuplicates(["cve_id"])
        .withColumn("published_date", F.to_date("published_datetime"))
        .withColumn("last_modified_date", F.to_date("last_modified_datetime"))
        .withColumn("published_year", F.year("published_date"))
        .withColumn("published_month", F.month("published_date"))
    )

    return silver_nvd


def write_dataframe(dataframe: DataFrame, output_path: str, partition_columns: list[str] | None = None) -> None:
    writer = dataframe.write.mode("overwrite")
    if partition_columns:
        writer = writer.partitionBy(*partition_columns)
    writer.parquet(output_path)


def print_summary(table_name: str, dataframe: DataFrame) -> None:
    print(f"\n========== {table_name} ==========")
    print(f"Rows: {dataframe.count():,}")
    dataframe.printSchema()
    dataframe.show(5, truncate=80)


def main() -> None:
    spark = create_spark_session("BuildSilverTables")

    try:
        silver_kev = build_silver_kev(spark)
        silver_epss = build_silver_epss(spark)
        silver_nvd = build_silver_nvd(spark)

        write_dataframe(
            silver_kev,
            str(SILVER_DIR / "silver_kev"),
            partition_columns=["date_added_year", "date_added_month"],
        )
        write_dataframe(
            silver_epss,
            str(SILVER_DIR / "silver_epss"),
            partition_columns=["epss_year", "epss_month"],
        )
        write_dataframe(
            silver_nvd,
            str(SILVER_DIR / "silver_nvd"),
            partition_columns=["published_year", "published_month"],
        )

        print_summary("Silver KEV", silver_kev)
        print_summary("Silver EPSS", silver_epss)
        print_summary("Silver NVD", silver_nvd)
        print("\nSilver tables built successfully.")

    finally:
        spark.stop()


if __name__ == "__main__":
    main()
