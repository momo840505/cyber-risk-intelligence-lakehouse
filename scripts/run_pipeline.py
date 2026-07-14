import subprocess
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]


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
        print("\n" + "!" * 80)
        print(f"Pipeline failed at step: {step_name}")
        print("!" * 80)
        raise SystemExit(completed_process.returncode)

    print(f"\nStep completed successfully: {step_name}")


def main() -> None:
    python_executable = sys.executable

    pipeline_steps = [
        (
            [python_executable, "scripts/run_ingestion.py"],
            "Bronze ingestion",
        ),
        (
            [python_executable, "-m", "cyber_risk.etl.build_silver_tables"],
            "Build Silver tables",
        ),
        (
            [python_executable, "-m", "cyber_risk.etl.build_gold_tables"],
            "Build Gold tables",
        ),
        (
            [python_executable, "scripts/validate_lakehouse.py"],
            "Validate Gold tables",
        ),
        (
            [python_executable, "scripts/run_dbt.py"],
            "Build dbt analytics marts",
        ),
        (
            [python_executable, "scripts/inspect_lakehouse.py"],
            "Inspect lakehouse outputs",
        ),

    ]

    print("\nCyber Risk Intelligence Lakehouse Pipeline")
    print("This command runs ingestion, ETL, validation, and inspection.")

    for command, step_name in pipeline_steps:
        run_command(command, step_name)

    print("\n" + "=" * 80)
    print("Pipeline completed successfully.")
    print("=" * 80)


if __name__ == "__main__":
    main()
