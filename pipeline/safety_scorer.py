"""Safety scoring engine.

Approach: Match user location to nearest district (sigungu),
then compare that district's metrics against all districts.
Buffer radius is kept for map display only.

Computes per-category safety levels using percentile ranking,
then applies time-weighted average across location types.
"""

import logging
from dataclasses import dataclass

import numpy as np
import pandas as pd

from config import LOCATION_WEIGHTS, LEVEL_THRESHOLDS, SAFETY_CATEGORIES
from llm.guide_generator import SafetySummary

logger = logging.getLogger(__name__)


# Seoul district centroids for matching
DISTRICT_CENTROIDS = {
    "종로구": (37.5735, 126.9790), "중구": (37.5641, 126.9979),
    "용산구": (37.5326, 126.9909), "성동구": (37.5633, 127.0369),
    "광진구": (37.5385, 127.0823), "동대문구": (37.5744, 127.0396),
    "중랑구": (37.6063, 127.0928), "성북구": (37.5894, 127.0164),
    "강북구": (37.6396, 127.0257), "도봉구": (37.6688, 127.0471),
    "노원구": (37.6543, 127.0568), "은평구": (37.6027, 126.9291),
    "서대문구": (37.5791, 126.9368), "마포구": (37.5663, 126.9014),
    "양천구": (37.5170, 126.8665), "강서구": (37.5510, 126.8495),
    "구로구": (37.4954, 126.8874), "금천구": (37.4569, 126.8955),
    "영등포구": (37.5264, 126.8963), "동작구": (37.5124, 126.9393),
    "관악구": (37.4784, 126.9516), "서초구": (37.4837, 127.0324),
    "강남구": (37.5172, 127.0473), "송파구": (37.5145, 127.1050),
    "강동구": (37.5301, 127.1238),
}


@dataclass
class LocationInput:
    """User-specified location."""
    location_type: str   # home / work / other
    latitude: float
    longitude: float
    label: str = ""


def haversine_km(lat1, lon1, lat2, lon2):
    """Haversine distance between two points in km."""
    R = 6371.0
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
    return R * 2 * np.arcsin(np.sqrt(a))


def match_district(lat, lng):
    """Find the nearest Seoul district to given coordinates.

    Returns:
        (district_name, distance_km)
    """
    best_name = None
    best_dist = float("inf")
    for name, (dlat, dlng) in DISTRICT_CENTROIDS.items():
        d = haversine_km(lat, lng, dlat, dlng)
        if d < best_dist:
            best_dist = d
            best_name = name
    return best_name, round(best_dist, 2)


def match_district_in_df(df, district_name):
    """Filter DataFrame rows matching a district name.

    Handles variations like '서울특별시 강남구1', '서울 강남구', '강남구'.
    """
    if df.empty:
        return df

    for col in ["sigungu", "gu", "station_name"]:
        if col in df.columns:
            mask = df[col].astype(str).str.contains(district_name, na=False)
            if mask.any():
                return df[mask].copy()

    return pd.DataFrame()


def percentile_level(value, distribution):
    """Assign green/yellow/red level based on percentile in distribution."""
    if len(distribution) == 0:
        return "green", 0.0
    pct = (np.searchsorted(np.sort(distribution), value) / len(distribution)) * 100
    for level, (lo, hi) in LEVEL_THRESHOLDS.items():
        if lo <= pct < hi:
            return level, round(pct, 1)
    return "red", round(pct, 1)


def _group_col(df, candidates):
    """Find which grouping column exists in the DataFrame."""
    for col in candidates:
        if col in df.columns:
            return col
    return None


def score_traffic(df_district, df_all):
    if df_district.empty:
        return "green", 0.0, "No traffic accident data for this district."
    count = df_district["accident_count"].sum()
    gcol = _group_col(df_all, ["sigungu", "sido"])
    if gcol:
        all_counts = df_all.groupby(gcol)["accident_count"].sum().values
    else:
        return "yellow", 50.0, f"Accidents: {count}"
    level, pct = percentile_level(count, all_counts)
    return level, pct, f"District accidents: {count} (percentile {pct:.0f}%)"


def score_crime(df_district, df_all):
    if df_district.empty:
        return "green", 0.0, "No crime data for this district."
    count = df_district["occurrence"].sum()
    gcol = _group_col(df_all, ["sigungu", "sido"])
    if gcol:
        all_counts = df_all.groupby(gcol)["occurrence"].sum().values
    else:
        return "yellow", 50.0, f"Crime occurrences: {count}"
    level, pct = percentile_level(count, all_counts)
    return level, pct, f"District crime: {count} (percentile {pct:.0f}%)"


def score_air_quality(df_district, df_all):
    if df_district.empty:
        return "green", 0.0, "No air quality data for this district."
    avg_pm25 = df_district["pm25"].mean()
    all_avgs = df_all.groupby("station_name")["pm25"].mean().dropna().values
    if len(all_avgs) == 0:
        return "yellow", 50.0, f"PM2.5 avg: {avg_pm25:.1f}"
    level, pct = percentile_level(avg_pm25, all_avgs)
    return level, pct, f"PM2.5 avg: {avg_pm25:.1f} ug/m3 (percentile {pct:.0f}%)"


def score_medical_access(df_district, df_all):
    if df_district.empty:
        return "red", 90.0, "No medical facility data for this district."
    count = len(df_district)
    gcol = _group_col(df_all, ["sigungu", "sido"])
    if gcol:
        all_counts = df_all.groupby(gcol).size().values
    else:
        return "yellow", 50.0, f"Medical facilities: {count}"
    level, pct = percentile_level(count, all_counts)
    inv_level = {"green": "red", "yellow": "yellow", "red": "green"}.get(level, level)
    inv_pct = 100 - pct
    return inv_level, inv_pct, f"Medical facilities: {count}"


def score_flood(df_district, df_all):
    if df_district.empty:
        return "green", 0.0, "No flood history for this district."
    count = len(df_district)
    gcol = _group_col(df_all, ["gu", "sigungu"])
    if gcol:
        all_counts = df_all.groupby(gcol).size().values
    else:
        return "yellow", 50.0, f"Flood records: {count}"
    level, pct = percentile_level(count, all_counts)
    return level, pct, f"Flood records: {count} (percentile {pct:.0f}%)"


def score_fire(df_district, df_all):
    if df_district.empty:
        return "green", 0.0, "No fire data for this district."
    count = df_district["fire_count"].sum()
    gcol = _group_col(df_all, ["sigungu", "sido"])
    if gcol:
        all_counts = df_all.groupby(gcol)["fire_count"].sum().values
    else:
        return "yellow", 50.0, f"Fires: {count}"
    level, pct = percentile_level(count, all_counts)
    return level, pct, f"District fires: {count} (percentile {pct:.0f}%)"


SCORERS = {
    "traffic": score_traffic,
    "crime": score_crime,
    "air_quality": score_air_quality,
    "medical_access": score_medical_access,
    "flood": score_flood,
    "fire": score_fire,
}


def compute_safety_summaries(locations, datasets, transport_mode="car"):
    """Compute safety summaries for all locations and categories.

    Strategy:
    1. Match each location to its nearest district.
    2. Filter data for that district only.
    3. Compare district metrics against all-district distribution.
    """
    summaries = []

    for loc in locations:
        district, dist_km = match_district(loc.latitude, loc.longitude)
        logger.info(
            "Location '%s' matched to %s (%.1f km)",
            loc.label or loc.location_type, district, dist_km,
        )

        for cat in SAFETY_CATEGORIES:
            df_all = datasets.get(cat, pd.DataFrame())
            if df_all.empty:
                continue

            df_district = match_district_in_df(df_all, district)
            scorer = SCORERS.get(cat)
            if scorer is None:
                continue

            level, score, detail = scorer(df_district, df_all)
            summaries.append(SafetySummary(
                category=cat,
                level=level,
                score=score,
                detail=f"[{district}] {detail}",
                location_type=loc.location_type,
            ))

    return summaries


def weighted_summary(summaries):
    """Compute time-weighted average safety level per category."""
    cat_scores = {}
    for s in summaries:
        w = LOCATION_WEIGHTS.get(s.location_type, 0.05)
        if s.category not in cat_scores:
            cat_scores[s.category] = {"weighted_score": 0.0, "total_weight": 0.0}
        cat_scores[s.category]["weighted_score"] += s.score * w
        cat_scores[s.category]["total_weight"] += w

    result = {}
    for cat, vals in cat_scores.items():
        if vals["total_weight"] > 0:
            avg = vals["weighted_score"] / vals["total_weight"]
        else:
            avg = 0.0
        for level, (lo, hi) in LEVEL_THRESHOLDS.items():
            if lo <= avg < hi:
                result[cat] = {"level": level, "score": round(avg, 1)}
                break
        else:
            result[cat] = {"level": "red", "score": round(avg, 1)}

    return result
