from pathlib import Path

import duckdb
import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
GOLD_DIR = BASE_DIR / "data" / "gold"
ANALYTICS_DIR = BASE_DIR / "analytics"
DATABASE_PATH = ANALYTICS_DIR / "cyber_risk.duckdb"


GOLD_TABLES = {
    "raw_vulnerability_priority": "vulnerability_priority",
    "raw_vendor_risk_summary": "vendor_risk_summary",
    "raw_monthly_vulnerability_trends": "monthly_vulnerability_trends",
    "raw_cwe_risk_summary": "cwe_risk_summary",
}


def load_gold_table(table_folder_name: str) -> pd.DataFrame:
    table_path = GOLD_DIR / table_folder_name

    if not table_path.exists():
        raise FileNotFoundError(
            f"Missing Gold table folder: {table_path}. "
            "Run the Gold ETL before building the analytics database."
        )

    return pd.read_parquet(table_path)


def write_table_to_duckdb(
    connection: duckdb.DuckDBPyConnection,
    dataframe: pd.DataFrame,
    table_name: str,
) -> None:
    temporary_view_name = f"{table_name}_view"

    connection.register(temporary_view_name, dataframe)
    connection.execute(
        f"CREATE OR REPLACE TABLE {table_name} AS SELECT * FROM {temporary_view_name}"
    )
    connection.unregister(temporary_view_name)


def main() -> None:
    ANALYTICS_DIR.mkdir(parents=True, exist_ok=True)

    print("\n========== Build Analytics DuckDB Database ==========")
    print(f"Database path: {DATABASE_PATH}")

    with duckdb.connect(str(DATABASE_PATH)) as connection:
        for duckdb_table_name, gold_folder_name in GOLD_TABLES.items():
            dataframe = load_gold_table(gold_folder_name)

            write_table_to_duckdb(
                connection=connection,
                dataframe=dataframe,
                table_name=duckdb_table_name,
            )

            print(
                f"[OK] Loaded {gold_folder_name} "
                f"into {duckdb_table_name}: {len(dataframe):,} rows"
            )

        tables = connection.execute("SHOW TABLES").fetchdf()

    print("\nAvailable tables:")
    print(tables.to_string(index=False))

    print("\nAnalytics database build completed successfully.")


if __name__ == "__main__":
    main()
