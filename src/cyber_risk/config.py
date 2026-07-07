from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATA_DIR = PROJECT_ROOT / "data"

BRONZE_DIR = DATA_DIR / "bronze"
SILVER_DIR = DATA_DIR / "silver"
GOLD_DIR = DATA_DIR / "gold"

KEV_BRONZE_DIR = BRONZE_DIR / "kev"
EPSS_BRONZE_DIR = BRONZE_DIR / "epss"
NVD_BRONZE_DIR = BRONZE_DIR / "nvd"

KEV_JSON_URL = (
    "https://raw.githubusercontent.com/cisagov/kev-data/develop/"
    "known_exploited_vulnerabilities.json"
)

EPSS_API_URL = "https://api.first.org/data/v1/epss"

NVD_CVE_API_URL = "https://services.nvd.nist.gov/rest/json/cves/2.0"


def create_project_directories() -> None:
    directories = [
        KEV_BRONZE_DIR,
        EPSS_BRONZE_DIR,
        NVD_BRONZE_DIR,
        SILVER_DIR,
        GOLD_DIR,
    ]

    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)