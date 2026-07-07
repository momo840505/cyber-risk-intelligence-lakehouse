from pyspark.sql import SparkSession


def create_spark_session(app_name: str = "CyberRiskIntelligenceLakehouse") -> SparkSession:
    """
    Create a local Spark session.

    Later, this same ETL logic can be moved to AWS Glue or EMR.
    """
    spark = (
        SparkSession.builder
        .appName(app_name)
        .master("local[*]")
        .config("spark.sql.shuffle.partitions", "8")
        .config("spark.sql.execution.arrow.pyspark.enabled", "true")
        .getOrCreate()
    )

    spark.sparkContext.setLogLevel("WARN")
    return spark