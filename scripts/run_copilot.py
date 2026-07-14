import subprocess
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]


def main() -> None:
    command = [sys.executable, "rag/remediation_copilot.py"]

    print("\n========== Cyber Risk Remediation Copilot ==========")
    print("This tool retrieves defensive remediation guidance for a CVE.")
    print("Command:", " ".join(command))

    subprocess.run(command, cwd=BASE_DIR, shell=False)


if __name__ == "__main__":
    main()