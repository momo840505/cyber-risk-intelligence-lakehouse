import subprocess
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]


def main() -> None:
    command = [
        sys.executable,
        "-m",
        "uvicorn",
        "api.main:app",
        "--host",
        "127.0.0.1",
        "--port",
        "8000",
        "--reload",
    ]

    print("\n========== Start Cyber Risk Intelligence API ==========")
    print("API URL: http://127.0.0.1:8000")
    print("Swagger UI: http://127.0.0.1:8000/docs")
    print("Press Ctrl + C to stop the API.")
    print("Command:", " ".join(command))

    subprocess.run(command, cwd=BASE_DIR, shell=False)


if __name__ == "__main__":
    main()