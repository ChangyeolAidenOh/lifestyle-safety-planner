"""Collector for fire statistics.

Source: 소방청 화재 통계
Download: KOSIS (kosis.kr) or nfa.go.kr → CSV
Manual download required.

Steps:
1. Visit https://kosis.kr
2. Search: "소방청_화재발생현황" or "시도별 화재 발생"
3. Select: 시도, 시군구, 화재건수, 사망, 부상, 재산피해, 원인
4. Download CSV → save to data/raw/fire_raw.csv
5. Run: python collectors/fire.py
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
    "fire_count": ["화재건수", "건수", "발생건수", "fire_count"],
    "death_count": ["사망", "사망자", "death_count"],
    "injury_count": ["부상", "부상자", "injury_count"],
    "property_damage": ["재산피해", "피해액", "property_damage"],
    "cause": ["원인", "화재원인", "cause"],
}


def find_column(df, candidates):
    for c in candidates:
        for col in df.columns:
            if c in col:
                return col
    return None


def parse_fire_csv(filepath):
    """Parse fire statistics CSV from KOSIS/NFA."""
    df = pd.read_csv(filepath, encoding="utf-8-sig")

    if df.empty:
        df = pd.read_csv(filepath, encoding="cp949")

    col_map = {}
    for target, candidates in EXPECTED_COLUMNS.items():
        found = find_column(df, candidates)
        if found:
            col_map[found] = target

    df = df.rename(columns=col_map)

    if "fire_count" not in df.columns and "sido" not in df.columns:
        logger.warning("Cannot find key columns. Available: %s", list(df.columns))
        return pd.DataFrame()

    # Clean numeric columns
    for col in ["fire_count", "death_count", "injury_count", "property_damage"]:
        if col in df.columns:
            df[col] = pd.to_numeric(
                df[col].astype(str).str.replace(",", ""), errors="coerce"
            ).fillna(0).astype(int)
        else:
            df[col] = 0

    if "year" not in df.columns:
        df["year"] = 2023

    for col in ["sido", "sigungu", "cause"]:
        if col not in df.columns:
            df[col] = ""

    return df[["year", "sido", "sigungu", "fire_count",
               "death_count", "injury_count", "property_damage", "cause"]]


def collect_and_save(filepath=None, output_dir=None):
    """Parse fire CSV and save."""
    if filepath is None:
        filepath = RAW_DIR / "fire_raw.csv"

    if output_dir is None:
        output_dir = RAW_DIR

    if not Path(filepath).exists():
        print(f"CSV not found: {filepath}")
        print("Download from KOSIS (kosis.kr) and save as data/raw/fire_raw.csv")
        print("Using existing sample data instead.")
        return None

    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(SAMPLE_DIR, exist_ok=True)

    print(f"Parsing fire data from {filepath}...")
    df = parse_fire_csv(filepath)

    if df.empty:
        print("Parse failed. Check CSV format.")
        return None

    # Filter Seoul
    df_seoul = df[df["sido"].str.contains("서울", na=False)].copy()

    raw_path = Path(output_dir) / "fire_stats.csv"
    df.to_csv(raw_path, index=False, encoding="utf-8-sig")
    print(f"Saved (full): {raw_path} ({len(df)} rows)")

    sample_path = SAMPLE_DIR / "safety_fire.csv"
    df_seoul.to_csv(sample_path, index=False, encoding="utf-8-sig")
    print(f"Saved (Seoul): {sample_path} ({len(df_seoul)} rows)")

    return df


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    df = collect_and_save()
    if df is not None:
        print(f"\nSample:\n{df.head()}")
        print(f"\nSido counts:\n{df['sido'].value_counts().head()}")
