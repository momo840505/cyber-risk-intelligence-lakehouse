import time
from typing import Any

import requests


def get_json(
    url: str,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    retries: int = 3,
    sleep_seconds: int = 3,
) -> dict[str, Any]:
    """
    Make a GET request and return JSON data.

    The retry logic makes the ingestion pipeline more reliable when
    a public data API is temporarily slow or unavailable.
    """
    last_error: Exception | None = None

    for attempt in range(1, retries + 1):
        try:
            response = requests.get(url, params=params, headers=headers, timeout=60)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as error:
            last_error = error
            print(f"Request failed on attempt {attempt}/{retries}: {error}")
            time.sleep(sleep_seconds)

    raise RuntimeError(f"Request failed after {retries} attempts") from last_error