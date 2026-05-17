"""Collector for flood history data.

Source: 서울시 침수흔적도
Download: data.seoul.go.kr → "침수흔적" 검색 → CSV
Manual download required.

Steps:
1. Visit https://data.seoul.go.kr
2. Search: "침수흔적" or "침수 이력"
3. Download CSV → save to data/raw/flood_raw.csv
4. Run: python collectors/flood.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import os
import logging

import pandas as pd

from config import RAW_DIR, SAMPLE_DIR

logger = logging.getLogger(__name__)

EXPECTED_COLUMNS = {
    "year": ["연도", "year", "발생년도", "발생연도"],
    "gu": ["자치구", "구", "gu", "시군구"],
    "dong": ["행정동", "동", "dong", "법정동"],
    "address": ["주소", "address", "소재지", "위치"],
    "latitude": ["위도", "latitude", "lat", "Y좌표"],
    "longitude": ["경도", "longitude", "lng", "lon", "X좌표"],
    "flood_depth_cm": ["침수깊이", "침수심", "depth", "깊이"],
}


def find_column(df, candidates):
    for c in candidates:
        for col in df.columns:
            if c in col:
                return col
    return None


def parse_flood_csv(filepath):
    """Parse flood history CSV from Seoul Open Data."""
    df = pd.read_csv(filepath, encoding="utf-8-sig")

    if df.empty:
        df = pd.read_csv(filepath, encoding="cp949")

    col_map = {}
    for target, candidates in EXPECTED_COLUMNS.items():
        found = find_column(df, candidates)
        if found:
            col_map[found] = target

    df = df.rename(columns=col_map)

    # Extract gu from address if gu column missing
    if "gu" not in df.columns and "address" in df.columns:
        df["gu"] = df["address"].str.extract(r"([\w]+구)")

    if "gu" not in df.columns:
        logger.warning("Cannot find district column. Available: %s", list(df.columns))
        return pd.DataFrame()

    # Parse numeric fields
    if "flood_depth_cm" in df.columns:
        df["flood_depth_cm"] = pd.to_numeric(
            df["flood_depth_cm"], errors="coerce"
        ).fillna(0).astype(int)
    else:
        df["flood_depth_cm"] = 0

    for coord in ["latitude", "longitude"]:
        if coord in df.columns:
            df[coord] = pd.to_numeric(df[coord], errors="coerce")

    if "year" not in df.columns:
        df["year"] = 2022

    if "dong" not in df.columns:
        df["dong"] = ""

    if "address" not in df.columns:
        df["address"] = ""

    return df[["year", "gu", "dong", "address", "latitude", "longitude", "flood_depth_cm"]]


def collect_and_save(filepath=None, output_dir=None):
    """Parse flood CSV and save."""
    if filepath is None:
        filepath = RAW_DIR / "flood_raw.csv"

    if output_dir is None:
        output_dir = RAW_DIR

    if not Path(filepath).exists():
        print(f"CSV not found: {filepath}")
        print("Download from data.seoul.go.kr and save as data/raw/flood_raw.csv")
        print("Using existing sample data instead.")
        return None

    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(SAMPLE_DIR, exist_ok=True)

    print(f"Parsing flood data from {filepath}...")
    df = parse_flood_csv(filepath)

    if df.empty:
        print("Parse failed. Check CSV format.")
        return None

    raw_path = Path(output_dir) / "flood_history.csv"
    df.to_csv(raw_path, index=False, encoding="utf-8-sig")
    print(f"Saved: {raw_path} ({len(df)} rows)")

    sample_path = SAMPLE_DIR / "safety_flood.csv"
    df.to_csv(sample_path, index=False, encoding="utf-8-sig")
    print(f"Saved: {sample_path} ({len(df)} rows)")

    return df


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    df = collect_and_save()
    if df is not None:
        print(f"\nSample:\n{df.head()}")
        print(f"\nGu counts:\n{df['gu'].value_counts()}")
