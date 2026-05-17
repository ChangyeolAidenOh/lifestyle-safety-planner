"""Collector for air quality data.

Source: 한국환경공단_에어코리아_대기오염정보
API: apis.data.go.kr/B552584/ArpltnInforInqireSvc
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import os
import logging
import time

import requests
import pandas as pd

from config import AIRKOREA_API_KEY, DATA_GO_KR_API_KEY, RAW_DIR, SAMPLE_DIR

logger = logging.getLogger(__name__)

# Use AIRKOREA key if set, otherwise fall back to DATA_GO_KR key
def _get_api_key():
    return AIRKOREA_API_KEY or DATA_GO_KR_API_KEY

# Endpoints
STATION_LIST_URL = "http://apis.data.go.kr/B552584/MsrstnInfoInqireSvc/getMsrstnList"
REALTIME_URL = "http://apis.data.go.kr/B552584/ArpltnInforInqireSvc/getMsrstnAcctoRltmMesureDnsty"
DAILY_URL = "http://apis.data.go.kr/B552584/ArpltnStatsSvc/getMsrstnAcctoRDyrg"

# Seoul measurement stations
SEOUL_STATIONS = [
    "종로구", "중구", "용산구", "성동구", "광진구",
    "동대문구", "중랑구", "성북구", "강북구", "도봉구",
    "노원구", "은평구", "서대문구", "마포구", "양천구",
    "강서구", "구로구", "금천구", "영등포구", "동작구",
    "관악구", "서초구", "강남구", "송파구", "강동구",
]


def fetch_station_list(sido="서울"):
    """Fetch measurement station list for a region."""
    api_key = _get_api_key()
    if not api_key:
        logger.error("No API key available for AirKorea.")
        return []

    params = {
        "serviceKey": api_key,
        "returnType": "json",
        "numOfRows": "100",
        "pageNo": "1",
        "addr": sido,
    }

    try:
        resp = requests.get(STATION_LIST_URL, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        items = data.get("response", {}).get("body", {}).get("items", [])
        return items if isinstance(items, list) else []
    except Exception as e:
        logger.error("Station list fetch failed: %s", e)
        return []


def fetch_daily_air_quality(station_name, period="MONTH"):
    """Fetch daily air quality for a station.

    Args:
        station_name: measurement station name (e.g., "종로구")
        period: MONTH or 3MONTH

    Returns:
        list of dicts
    """
    api_key = _get_api_key()
    if not api_key:
        return []

    params = {
        "serviceKey": api_key,
        "returnType": "json",
        "numOfRows": "100",
        "pageNo": "1",
        "stationName": station_name,
        "dataTerm": period,
        "ver": "1.0",
    }

    try:
        resp = requests.get(REALTIME_URL, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        items = data.get("response", {}).get("body", {}).get("items", [])
        return items if isinstance(items, list) else []
    except Exception as e:
        logger.warning("  %s failed: %s", station_name, e)
        return []


def collect_seoul_air_quality(stations=None, period="MONTH"):
    """Collect air quality data for Seoul stations.

    Args:
        stations: list of station names (default: all Seoul districts)
        period: MONTH or 3MONTH

    Returns:
        list of dicts
    """
    if stations is None:
        stations = SEOUL_STATIONS

    all_rows = []

    for station in stations:
        items = fetch_daily_air_quality(station, period)

        for item in items:
            def safe_float(val):
                try:
                    return float(val) if val and val != "-" else None
                except (ValueError, TypeError):
                    return None

            all_rows.append({
                "measure_date": item.get("dataTime", ""),
                "station_name": station,
                "sido": "서울특별시",
                "pm10": safe_float(item.get("pm10Value")),
                "pm25": safe_float(item.get("pm25Value")),
                "o3": safe_float(item.get("o3Value")),
                "no2": safe_float(item.get("no2Value")),
                "co": safe_float(item.get("coValue")),
                "so2": safe_float(item.get("so2Value")),
                "aqi": safe_float(item.get("khaiValue")),
            })

        logger.info("  %s: %d records", station, len(items))
        time.sleep(0.5)  # rate limit (500 calls/day)

    return all_rows


def collect_and_save(stations=None, output_dir=None):
    """Collect air quality data and save as CSV."""
    if output_dir is None:
        output_dir = RAW_DIR

    os.makedirs(output_dir, exist_ok=True)

    print("Fetching Seoul air quality data...")
    rows = collect_seoul_air_quality(stations)

    if not rows:
        print("No data collected. Check API key and connection.")
        return

    df = pd.DataFrame(rows)
    df["measure_date"] = pd.to_datetime(df["measure_date"], errors="coerce")

    # Save to raw
    raw_path = Path(output_dir) / "air_quality.csv"
    df.to_csv(raw_path, index=False, encoding="utf-8-sig")
    print(f"Saved: {raw_path} ({len(df)} rows)")

    # Also save to sample for dashboard
    sample_path = SAMPLE_DIR / "safety_air_quality.csv"
    os.makedirs(SAMPLE_DIR, exist_ok=True)
    df.to_csv(sample_path, index=False, encoding="utf-8-sig")
    print(f"Saved: {sample_path} ({len(df)} rows)")

    return df


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Test with 3 stations first
    print("=== Testing with 3 stations ===")
    df = collect_and_save(stations=["종로구", "강남구", "마포구"])

    if df is not None:
        print(f"\nSample:\n{df.head()}")
        print(f"\nColumns: {list(df.columns)}")
        print(f"\nStation counts:\n{df['station_name'].value_counts()}")
        print(f"\nPM2.5 stats:\n{df['pm25'].describe()}")
