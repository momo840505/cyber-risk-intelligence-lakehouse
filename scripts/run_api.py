import os
import subprocess
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]

API_HOST = os.getenv("API_HOST", "127.0.0.1")
API_PORT = os.getenv("API_PORT", "8001")


def main() -> None:
    command = [
        sys.executable,
        "-m",
        "uvicorn",
        "api.main:app",
        "--host",
        API_HOST,
        "--port",
        API_PORT,
    ]

    print("\n========== Cyber Risk Intelligence API ==========")
    print(f"API URL: http://{API_HOST}:{API_PORT}")
    print(f"Swagger UI: http://{API_HOST}:{API_PORT}/docs")
    print(f"Metrics: http://{API_HOST}:{API_PORT}/metrics")
    print("Command:", " ".join(command))

    subprocess.run(command, cwd=BASE_DIR, shell=False)


if __name__ == "__main__":
    main()
