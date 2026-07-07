from cyber_risk.ingestion.download_epss import download_epss_top_scores
from cyber_risk.ingestion.download_kev import download_kev_catalog
from cyber_risk.ingestion.download_nvd_recent import download_recent_nvd_cves


def main() -> None:
    print("Starting ingestion pipeline...")

    download_kev_catalog()
    download_epss_top_scores(limit=5000)
    download_recent_nvd_cves(days_back=30)

    print("Ingestion pipeline completed.")


if __name__ == "__main__":
    main()