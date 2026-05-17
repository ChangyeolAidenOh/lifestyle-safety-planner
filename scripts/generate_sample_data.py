"""Generate sample CSV data for development and Streamlit Cloud demo.

Run: python scripts/generate_sample_data.py
"""

import os
import sys
import random
from pathlib import Path

import numpy as np
import pandas as pd

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import SAMPLE_DIR

random.seed(42)
np.random.seed(42)

# Seoul district centroids (approximate)
SEOUL_DISTRICTS = {
    "종로구": (37.5735, 126.9790),
    "중구": (37.5641, 126.9979),
    "용산구": (37.5326, 126.9909),
    "성동구": (37.5633, 127.0369),
    "광진구": (37.5385, 127.0823),
    "동대문구": (37.5744, 127.0396),
    "중랑구": (37.6063, 127.0928),
    "성북구": (37.5894, 127.0164),
    "강북구": (37.6396, 127.0257),
    "도봉구": (37.6688, 127.0471),
    "노원구": (37.6543, 127.0568),
    "은평구": (37.6027, 126.9291),
    "서대문구": (37.5791, 126.9368),
    "마포구": (37.5663, 126.9014),
    "양천구": (37.5170, 126.8665),
    "강서구": (37.5510, 126.8495),
    "구로구": (37.4954, 126.8874),
    "금천구": (37.4569, 126.8955),
    "영등포구": (37.5264, 126.8963),
    "동작구": (37.5124, 126.9393),
    "관악구": (37.4784, 126.9516),
    "서초구": (37.4837, 127.0324),
    "강남구": (37.5172, 127.0473),
    "송파구": (37.5145, 127.1050),
    "강동구": (37.5301, 127.1238),
}


def jitter(lat, lng, spread=0.01):
    """Add random jitter to coordinates."""
    return (
        lat + np.random.uniform(-spread, spread),
        lng + np.random.uniform(-spread, spread),
    )


def gen_traffic():
    """Generate sample traffic accident data."""
    rows = []
    for gu, (lat, lng) in SEOUL_DISTRICTS.items():
        n_spots = random.randint(3, 15)
        for i in range(n_spots):
            jlat, jlng = jitter(lat, lng, 0.008)
            rows.append({
                "year": random.choice([2022, 2023, 2024]),
                "sido": "서울특별시",
                "sigungu": gu,
                "spot_name": f"{gu} 사고다발지 {i+1}",
                "latitude": round(jlat, 6),
                "longitude": round(jlng, 6),
                "accident_count": random.randint(3, 25),
                "death_count": random.randint(0, 3),
                "injury_count": random.randint(1, 30),
                "road_type": random.choice(["교차로", "단일로", "기타"]),
            })
    return pd.DataFrame(rows)


def gen_crime():
    """Generate sample crime statistics."""
    crime_types = ["절도", "폭력", "사기", "성범죄", "강도"]
    rows = []
    for gu, (lat, lng) in SEOUL_DISTRICTS.items():
        for year in [2022, 2023, 2024]:
            for ct in crime_types:
                rows.append({
                    "year": year,
                    "sido": "서울특별시",
                    "sigungu": gu,
                    "crime_type": ct,
                    "occurrence": random.randint(50, 500),
                    "arrest": random.randint(30, 300),
                })
    return pd.DataFrame(rows)


def gen_flood():
    """Generate sample flood history."""
    flood_gus = ["강남구", "서초구", "동작구", "관악구", "영등포구",
                 "송파구", "강동구", "마포구", "용산구", "성동구"]
    rows = []
    for gu in flood_gus:
        lat, lng = SEOUL_DISTRICTS[gu]
        n_records = random.randint(2, 20)
        for i in range(n_records):
            jlat, jlng = jitter(lat, lng, 0.005)
            rows.append({
                "year": random.choice([2020, 2022, 2023]),
                "gu": gu,
                "dong": f"{gu} 동{i+1}",
                "address": f"서울특별시 {gu} 임시주소 {i+1}",
                "latitude": round(jlat, 6),
                "longitude": round(jlng, 6),
                "flood_depth_cm": random.randint(10, 120),
            })
    return pd.DataFrame(rows)


def gen_medical():
    """Generate sample medical facility data."""
    facility_types = ["종합병원", "병원", "의원", "약국"]
    rows = []
    for gu, (lat, lng) in SEOUL_DISTRICTS.items():
        n_facilities = random.randint(10, 60)
        for i in range(n_facilities):
            jlat, jlng = jitter(lat, lng, 0.01)
            ft = random.choice(facility_types)
            rows.append({
                "facility_name": f"{gu} {ft} {i+1}",
                "facility_type": ft,
                "sido": "서울특별시",
                "sigungu": gu,
                "address": f"서울특별시 {gu} 임시주소 {i+1}",
                "latitude": round(jlat, 6),
                "longitude": round(jlng, 6),
                "bed_count": random.randint(0, 500) if ft in ("종합병원", "병원") else 0,
                "emergency_yn": ft == "종합병원" and random.random() > 0.3,
            })
    return pd.DataFrame(rows)


def gen_air_quality():
    """Generate sample air quality data."""
    stations = {
        "종로구": (37.572, 126.966),
        "중구": (37.564, 127.005),
        "강남구": (37.514, 127.065),
        "송파구": (37.515, 127.105),
        "마포구": (37.566, 126.901),
        "노원구": (37.654, 127.057),
        "강서구": (37.551, 126.850),
        "구로구": (37.495, 126.887),
        "영등포구": (37.526, 126.896),
        "관악구": (37.478, 126.952),
    }
    rows = []
    dates = pd.date_range("2024-01-01", "2024-12-31", freq="D")
    for station, (lat, lng) in stations.items():
        for d in dates:
            # Seasonal pattern: worse in spring (3-5) and winter (11-2)
            month = d.month
            seasonal = 15 if month in [3, 4, 5, 11, 12, 1, 2] else 5
            rows.append({
                "measure_date": d.strftime("%Y-%m-%d"),
                "station_name": station,
                "sido": "서울특별시",
                "pm10": round(max(5, np.random.normal(45 + seasonal, 20)), 1),
                "pm25": round(max(2, np.random.normal(25 + seasonal, 12)), 1),
                "o3": round(max(0, np.random.normal(0.03, 0.015)), 4),
                "no2": round(max(0, np.random.normal(0.03, 0.01)), 4),
                "co": round(max(0, np.random.normal(0.5, 0.2)), 2),
                "so2": round(max(0, np.random.normal(0.004, 0.002)), 4),
                "aqi": random.randint(20, 180),
            })
    return pd.DataFrame(rows)


def gen_fire():
    """Generate sample fire statistics."""
    causes = ["전기", "부주의", "방화", "담배", "불명"]
    rows = []
    for gu, (lat, lng) in SEOUL_DISTRICTS.items():
        for year in [2022, 2023, 2024]:
            for cause in causes:
                rows.append({
                    "year": year,
                    "sido": "서울특별시",
                    "sigungu": gu,
                    "fire_count": random.randint(5, 50),
                    "death_count": random.randint(0, 3),
                    "injury_count": random.randint(0, 10),
                    "property_damage": random.randint(1000, 500000),
                    "cause": cause,
                })
    return pd.DataFrame(rows)


def main():
    os.makedirs(SAMPLE_DIR, exist_ok=True)

    generators = {
        "safety_traffic": gen_traffic,
        "safety_crime": gen_crime,
        "safety_flood": gen_flood,
        "safety_medical_access": gen_medical,
        "safety_air_quality": gen_air_quality,
        "safety_fire": gen_fire,
    }

    for name, gen_fn in generators.items():
        df = gen_fn()
        path = SAMPLE_DIR / f"{name}.csv"
        df.to_csv(path, index=False)
        print(f"  {name}: {len(df)} rows -> {path}")

    print("Sample data generation complete.")


if __name__ == "__main__":
    main()
