import os

from cyber_risk.ingestion.download_epss import download_epss_scores
from cyber_risk.ingestion.download_kev import download_kev_catalog
from cyber_risk.ingestion.download_nvd_recent import download_recent_nvd_cves


def main() -> None:
    nvd_days_back = int(os.getenv("NVD_DAYS_BACK", "730"))
    print(f"Starting ingestion. NVD lookback: {nvd_days_back} days")

    download_kev_catalog()
    download_epss_scores()
    download_recent_nvd_cves(days_back=nvd_days_back)

    print("Ingestion completed.")


if __name__ == "__main__":
    main()
