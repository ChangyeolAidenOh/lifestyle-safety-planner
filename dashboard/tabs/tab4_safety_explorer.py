"""Tab 4: 지역 탐색 - 자유 지도 탐색."""

import streamlit as st
import folium
from streamlit_folium import st_folium
from folium.plugins import HeatMap

from pipeline.db import load_csv
from dashboard.tabs.tab1_safety_map import DISTRICT_COORDS


def render():
    st.markdown("지도에서 원하는 지역의 안전 데이터를 확인하세요.")

    layer = st.selectbox(
        "데이터 레이어",
        ["교통사고 다발지", "의료기관", "침수 이력", "대기질"],
        key="explorer_layer",
    )

    m = folium.Map(
        location=[37.5665, 126.9780], zoom_start=11, tiles="cartodbpositron",
    )

    if layer == "교통사고 다발지":
        df = load_csv("safety_traffic")
        if not df.empty and "latitude" in df.columns:
            heat_data = df[["latitude", "longitude", "accident_count"]].values.tolist()
            HeatMap(heat_data, radius=15, blur=20, max_zoom=13).add_to(m)

    elif layer == "의료기관":
        df = load_csv("safety_medical_access")
        if not df.empty and "latitude" in df.columns:
            for _, row in df.iterrows():
                color = "red" if row.get("emergency_yn") else "blue"
                folium.CircleMarker(
                    location=[row["latitude"], row["longitude"]],
                    radius=3, color=color, fill=True, fill_opacity=0.6,
                    popup=row.get("facility_name", ""),
                ).add_to(m)

    elif layer == "침수 이력":
        df = load_csv("safety_flood")
        if not df.empty and "latitude" in df.columns:
            for _, row in df.iterrows():
                folium.CircleMarker(
                    location=[row["latitude"], row["longitude"]],
                    radius=max(3, row.get("flood_depth_cm", 10) / 10),
                    color="#3b82f6", fill=True, fill_opacity=0.5,
                    popup=f"침수 깊이: {row.get('flood_depth_cm', '-')}cm ({row.get('year', '')}년)",
                ).add_to(m)

    elif layer == "대기질":
        df = load_csv("safety_air_quality")
        if not df.empty:
            avg = df.groupby("station_name")["pm25"].mean().reset_index()
            for _, row in avg.iterrows():
                station = row["station_name"]
                coords = DISTRICT_COORDS.get(station)
                if coords:
                    pm25_val = row["pm25"]
                    color = "#22c55e" if pm25_val < 25 else "#eab308" if pm25_val < 50 else "#ef4444"
                    label = "좋음" if pm25_val < 15 else "보통" if pm25_val < 35 else "나쁨"
                    folium.CircleMarker(
                        location=coords, radius=12,
                        color=color, fill=True, fill_opacity=0.6,
                        popup=f"{station}: PM2.5 평균 {pm25_val:.1f} ({label})",
                    ).add_to(m)

    st_folium(m, width="100%", height=550)
