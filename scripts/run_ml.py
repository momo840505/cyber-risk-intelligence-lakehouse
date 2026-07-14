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
        print(f"\nStep failed: {step_name}")
        raise SystemExit(completed_process.returncode)

    print(f"\nStep completed successfully: {step_name}")


def main() -> None:
    run_command(
        [sys.executable, "scripts/run_dbt.py"],
        "Build dbt analytics marts",
    )

    run_command(
        [sys.executable, "ml/train_priority_model.py"],
        "Train vulnerability priority classifier",
    )

    print("\nML workflow completed successfully.")


if __name__ == "__main__":
    main()