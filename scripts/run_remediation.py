import subprocess
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]


def main() -> None:
    command = [sys.executable, "rag/remediation_engine.py"]
    raise SystemExit(subprocess.run(command, cwd=BASE_DIR, shell=False).returncode)


if __name__ == "__main__":
    main()
