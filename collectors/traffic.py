"""Collector for traffic accident-prone areas.

Source: 한국도로교통공단_지자체별 교통사고 다발지역
API: apis.data.go.kr/B552061/frequentzoneStat
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import os
import logging
import time

import requests
import pandas as pd

from config import DATA_GO_KR_API_KEY, RAW_DIR, SAMPLE_DIR

logger = logging.getLogger(__name__)

BASE_URL = "http://apis.data.go.kr/B552061/frequentzoneLg/getRestFrequentzoneLg"

# 시도 코드 (TAAS 기준)
SIDO_CODES = {
    "서울": "11", "부산": "26", "대구": "27", "인천": "28",
    "광주": "29", "대전": "30", "울산": "31", "세종": "36",
    "경기": "41", "강원": "42", "충북": "43", "충남": "44",
    "전북": "45", "전남": "46", "경북": "47", "경남": "48",
    "제주": "50",
}


def fetch_traffic_accidents(year=2023, sido_code=None):
    """Fetch accident-prone area data from TAAS API.

    Args:
        year: target year
        sido_code: specific sido code or None for all

    Returns:
        list of dicts
    """
    if not DATA_GO_KR_API_KEY:
        logger.error("DATA_GO_KR_API_KEY not set.")
        return []

    codes = {sido_code: sido_code} if sido_code else SIDO_CODES
    all_rows = []

    for sido_name, code in codes.items():
        params = {
            "serviceKey": DATA_GO_KR_API_KEY,
            "searchYearCd": str(year),
            "siDo": code,
            "guGun": "",
            "type": "json",
            "numOfRows": "500",
            "pageNo": "1",
        }

        try:
            resp = requests.get(BASE_URL, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()

            items = (
                data.get("items", {}).get("item", [])
                if isinstance(data.get("items"), dict)
                else data.get("items", [])
            )

            if not items:
                # Try alternate response structure
                body = data.get("response", {}).get("body", {})
                items = body.get("items", {}).get("item", [])

            if isinstance(items, dict):
                items = [items]

            for item in items:
                all_rows.append({
                    "year": year,
                    "sido": item.get("sido_sgg_nm", "").split(" ")[0] if item.get("sido_sgg_nm") else sido_name,
                    "sigungu": item.get("sido_sgg_nm", ""),
                    "spot_name": item.get("spot_nm", ""),
                    "latitude": float(item.get("la_crd", 0) or 0),
                    "longitude": float(item.get("lo_crd", 0) or 0),
                    "accident_count": int(item.get("occrrnc_cnt", 0) or 0),
                    "death_count": int(item.get("dth_dnv_cnt", 0) or 0),
                    "injury_count": int(item.get("se_dnv_cnt", 0) or 0),
                    "road_type": item.get("occrrnc_lc_road_knd_nm", ""),
                })

            logger.info("  %s: %d records", sido_name, len(items))

        except Exception as e:
            logger.warning("  %s failed: %s", sido_name, e)

        time.sleep(0.3)  # rate limit

    return all_rows


def collect_and_save(years=None, output_dir=None):
    """Collect traffic accident data and save as CSV.

    Args:
        years: list of years to collect (default: [2022, 2023])
        output_dir: output directory (default: data/raw/)
    """
    if years is None:
        years = [2022, 2023]
    if output_dir is None:
        output_dir = RAW_DIR

    os.makedirs(output_dir, exist_ok=True)

    all_rows = []
    for year in years:
        print(f"Fetching traffic accidents for {year}...")
        rows = fetch_traffic_accidents(year=year)
        all_rows.extend(rows)
        print(f"  Total: {len(rows)} records")

    if not all_rows:
        print("No data collected. Check API key and connection.")
        return

    df = pd.DataFrame(all_rows)

    # Save to raw
    raw_path = Path(output_dir) / "traffic_accidents.csv"
    df.to_csv(raw_path, index=False, encoding="utf-8-sig")
    print(f"Saved: {raw_path} ({len(df)} rows)")

    # Also save to sample for dashboard
    sample_path = SAMPLE_DIR / "safety_traffic.csv"
    os.makedirs(SAMPLE_DIR, exist_ok=True)
    df.to_csv(sample_path, index=False, encoding="utf-8-sig")
    print(f"Saved: {sample_path} ({len(df)} rows)")

    return df


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    df = collect_and_save()
    if df is not None:
        print(f"\nSample:\n{df.head()}")
        print(f"\nColumns: {list(df.columns)}")
        print(f"Sido counts:\n{df['sido'].value_counts().head(10)}")
