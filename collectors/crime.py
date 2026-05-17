"""Collector for crime statistics.

Source: 경찰청 범죄 발생 통계
Download: KOSIS (kosis.kr) or data.go.kr → CSV
Manual download required (no open API for detailed district-level data).

Steps:
1. Visit https://kosis.kr
2. Search: "경찰청_범죄발생지_시군구" or "범죄 발생 지역별 통계"
3. Select: 시도, 시군구, 범죄유형, 발생건수, 검거건수
4. Download CSV → save to data/raw/crime_raw.csv
5. Run: python collectors/crime.py
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
    "year": ["연도", "year", "기간"],
    "sido": ["시도", "시도별", "sido"],
    "sigungu": ["시군구", "시군구별", "sigungu"],
    "crime_type": ["범죄유형", "범죄중분류", "crime_type"],
    "occurrence": ["발생건수", "발생", "occurrence"],
    "arrest": ["검거건수", "검거", "arrest"],
}


def find_column(df, candidates):
    """Find matching column name from candidates."""
    for c in candidates:
        for col in df.columns:
            if c in col:
                return col
    return None


def parse_crime_csv(filepath):
    """Parse crime CSV from KOSIS download.

    Handles various column name formats.
    """
    df = pd.read_csv(filepath, encoding="utf-8-sig")

    if df.empty:
        # Try cp949 encoding
        df = pd.read_csv(filepath, encoding="cp949")

    col_map = {}
    for target, candidates in EXPECTED_COLUMNS.items():
        found = find_column(df, candidates)
        if found:
            col_map[found] = target

    df = df.rename(columns=col_map)

    required = ["sido", "sigungu", "crime_type", "occurrence"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        logger.warning("Missing columns: %s. Available: %s", missing, list(df.columns))
        logger.info("Falling back to sample data.")
        return pd.DataFrame()

    # Clean numeric columns
    for col in ["occurrence", "arrest"]:
        if col in df.columns:
            df[col] = pd.to_numeric(
                df[col].astype(str).str.replace(",", ""), errors="coerce"
            ).fillna(0).astype(int)

    if "year" not in df.columns:
        df["year"] = 2023

    return df[["year", "sido", "sigungu", "crime_type", "occurrence",
               "arrest"] if "arrest" in df.columns else
              ["year", "sido", "sigungu", "crime_type", "occurrence"]]


def collect_and_save(filepath=None, output_dir=None):
    """Parse crime CSV and save to sample directory."""
    if filepath is None:
        filepath = RAW_DIR / "crime_raw.csv"

    if output_dir is None:
        output_dir = RAW_DIR

    if not Path(filepath).exists():
        print(f"CSV not found: {filepath}")
        print("Download from KOSIS (kosis.kr) and save as data/raw/crime_raw.csv")
        print("Using existing sample data instead.")
        return None

    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(SAMPLE_DIR, exist_ok=True)

    print(f"Parsing crime data from {filepath}...")
    df = parse_crime_csv(filepath)

    if df.empty:
        print("Parse failed. Check CSV format.")
        return None

    # Filter Seoul only for dashboard
    df_seoul = df[df["sido"].str.contains("서울", na=False)].copy()

    raw_path = Path(output_dir) / "crime_stats.csv"
    df.to_csv(raw_path, index=False, encoding="utf-8-sig")
    print(f"Saved (full): {raw_path} ({len(df)} rows)")

    sample_path = SAMPLE_DIR / "safety_crime.csv"
    df_seoul.to_csv(sample_path, index=False, encoding="utf-8-sig")
    print(f"Saved (Seoul): {sample_path} ({len(df_seoul)} rows)")

    return df


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    df = collect_and_save()
    if df is not None:
        print(f"\nSample:\n{df.head()}")
        print(f"\nSido counts:\n{df['sido'].value_counts().head()}")
