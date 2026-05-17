"""Collector for medical facility data.

Source: 건강보험심사평가원 의료기관 현황
Download: opendata.hira.or.kr → "의료기관" → CSV
Or: data.go.kr → "건강보험심사평가원_의료기관" → CSV/API

Steps:
1. Visit https://opendata.hira.or.kr
2. Search: "의료기관 현황" or "병원 정보"
3. Download CSV → save to data/raw/medical_raw.csv
4. Run: python collectors/medical.py
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
    "facility_name": ["요양기관명", "기관명", "병원명", "facility_name"],
    "facility_type": ["종별코드명", "종별", "기관유형", "facility_type"],
    "sido": ["시도코드명", "시도", "sido"],
    "sigungu": ["시군구코드명", "시군구", "sigungu"],
    "address": ["주소", "소재지", "address"],
    "latitude": ["좌표(Y)", "위도", "latitude", "Y좌표"],
    "longitude": ["좌표(X)", "경도", "longitude", "X좌표"],
    "bed_count": ["총병상수", "병상수", "bed_count"],
}


def find_column(df, candidates):
    for c in candidates:
        for col in df.columns:
            if c in col:
                return col
    return None


def parse_medical_csv(filepath):
    """Parse medical facility CSV from HIRA."""
    df = pd.read_csv(filepath, encoding="utf-8-sig")

    if df.empty:
        df = pd.read_csv(filepath, encoding="cp949")

    col_map = {}
    for target, candidates in EXPECTED_COLUMNS.items():
        found = find_column(df, candidates)
        if found:
            col_map[found] = target

    df = df.rename(columns=col_map)

    if "facility_name" not in df.columns:
        logger.warning("Cannot find facility name. Available: %s", list(df.columns))
        return pd.DataFrame()

    # Parse coordinates
    for coord in ["latitude", "longitude"]:
        if coord in df.columns:
            df[coord] = pd.to_numeric(df[coord], errors="coerce")

    # Parse bed count
    if "bed_count" in df.columns:
        df["bed_count"] = pd.to_numeric(df["bed_count"], errors="coerce").fillna(0).astype(int)
    else:
        df["bed_count"] = 0

    # Determine emergency capability
    if "facility_type" in df.columns:
        emergency_types = ["종합병원", "상급종합"]
        df["emergency_yn"] = df["facility_type"].str.contains(
            "|".join(emergency_types), na=False
        )
    else:
        df["facility_type"] = ""
        df["emergency_yn"] = False

    for col in ["sido", "sigungu", "address"]:
        if col not in df.columns:
            df[col] = ""

    return df[["facility_name", "facility_type", "sido", "sigungu",
               "address", "latitude", "longitude", "bed_count", "emergency_yn"]]


def collect_and_save(filepath=None, output_dir=None):
    """Parse medical CSV and save."""
    if filepath is None:
        filepath = RAW_DIR / "medical_raw.csv"

    if output_dir is None:
        output_dir = RAW_DIR

    if not Path(filepath).exists():
        print(f"CSV not found: {filepath}")
        print("Download from opendata.hira.or.kr and save as data/raw/medical_raw.csv")
        print("Using existing sample data instead.")
        return None

    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(SAMPLE_DIR, exist_ok=True)

    print(f"Parsing medical facility data from {filepath}...")
    df = parse_medical_csv(filepath)

    if df.empty:
        print("Parse failed. Check CSV format.")
        return None

    # Filter Seoul
    df_seoul = df[df["sido"].str.contains("서울", na=False)].copy()

    raw_path = Path(output_dir) / "medical_facilities.csv"
    df.to_csv(raw_path, index=False, encoding="utf-8-sig")
    print(f"Saved (full): {raw_path} ({len(df)} rows)")

    sample_path = SAMPLE_DIR / "safety_medical_access.csv"
    df_seoul.to_csv(sample_path, index=False, encoding="utf-8-sig")
    print(f"Saved (Seoul): {sample_path} ({len(df_seoul)} rows)")

    return df


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    df = collect_and_save()
    if df is not None:
        print(f"\nSample:\n{df.head()}")
        print(f"\nFacility types:\n{df['facility_type'].value_counts().head()}")
