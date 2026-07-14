import subprocess
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
DBT_PROJECT_DIR = BASE_DIR / "dbt" / "cyber_risk_dbt"
DBT_PROFILES_DIR = DBT_PROJECT_DIR


def run_command(command: list[str], step_name: str) -> None:
    print("\n" + "=" * 80)
    print(f"Running step: {step_name}")
    print("=" * 80)
    print("Command:", " ".join(command))

    completed_process = subprocess.run(
        command,
        cwd=BASE_DIR,
        shell=False,
    )

    if completed_process.returncode != 0:
        print(f"\nStep failed: {step_name}")
        raise SystemExit(completed_process.returncode)

    print(f"\nStep completed successfully: {step_name}")


def main() -> None:
    run_command(
        [sys.executable, "scripts/build_analytics_database.py"],
        "Build DuckDB analytics database",
    )

    run_command(
        [
            "dbt",
            "build",
            "--project-dir",
            str(DBT_PROJECT_DIR),
            "--profiles-dir",
            str(DBT_PROFILES_DIR),
        ],
        "Run dbt build",
    )

    run_command(
        [
            "dbt",
            "docs",
            "generate",
            "--project-dir",
            str(DBT_PROJECT_DIR),
            "--profiles-dir",
            str(DBT_PROFILES_DIR),
        ],
        "Generate dbt docs",
    )

    print("\nDBT analytics workflow completed successfully.")


if __name__ == "__main__":
    main()
