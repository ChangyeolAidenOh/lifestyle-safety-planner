"""Tab 1: 안전 지도 - Folium 지도 + 동선 오버레이."""

import streamlit as st
import folium
from streamlit_folium import st_folium

from pipeline.db import load_csv

DISTRICT_COORDS = {
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


def geocode_district(name):
    for district, coords in DISTRICT_COORDS.items():
        if district in name or name in district:
            return coords
    return (37.5665, 126.9780)


def render():
    if not st.session_state.get("profile_submitted"):
        st.info("왼쪽 프로필을 입력하고 '안전 체크 시작' 버튼을 눌러주세요.")
        return

    home = st.session_state.get("home_area", "강남구")
    work = st.session_state.get("work_area", "종로구")

    home_coords = geocode_district(home)
    work_coords = geocode_district(work)

    center_lat = (home_coords[0] + work_coords[0]) / 2
    center_lng = (home_coords[1] + work_coords[1]) / 2

    m = folium.Map(location=[center_lat, center_lng], zoom_start=12, tiles="cartodbpositron")

    folium.Marker(
        location=home_coords,
        popup=f"거주지: {home}",
        icon=folium.Icon(color="blue", icon="home", prefix="fa"),
    ).add_to(m)

    folium.Marker(
        location=work_coords,
        popup=f"직장: {work}",
        icon=folium.Icon(color="green", icon="briefcase", prefix="fa"),
    ).add_to(m)

    folium.PolyLine(
        locations=[home_coords, work_coords],
        weight=3, color="#6366f1", dash_array="10", opacity=0.7,
    ).add_to(m)

    # Traffic accident overlay
    df_traffic = load_csv("safety_traffic")
    if not df_traffic.empty and "latitude" in df_traffic.columns:
        from folium.plugins import MarkerCluster
        cluster = MarkerCluster(name="교통사고 다발지")
        for _, row in df_traffic.iterrows():
            folium.CircleMarker(
                location=[row["latitude"], row["longitude"]],
                radius=max(2, row.get("accident_count", 3) * 0.5),
                color="#ef4444", fill=True, fill_opacity=0.4,
                popup=f"{row.get('spot_name', '')} ({row.get('accident_count', '')}건)",
            ).add_to(cluster)
        cluster.add_to(m)

    # Emergency medical facilities overlay
    df_medical = load_csv("safety_medical_access")
    if not df_medical.empty and "latitude" in df_medical.columns:
        med_group = folium.FeatureGroup(name="응급의료기관", show=False)
        for _, row in df_medical.iterrows():
            if row.get("emergency_yn"):
                folium.Marker(
                    location=[row["latitude"], row["longitude"]],
                    popup=f"{row['facility_name']} (응급)",
                    icon=folium.Icon(color="red", icon="plus", prefix="fa"),
                ).add_to(med_group)
        med_group.add_to(m)

    folium.LayerControl().add_to(m)
    st_folium(m, width="100%", height=500)

    cols = st.columns(3)
    labels = [("양호", "#22c55e"), ("주의", "#eab308"), ("경고", "#ef4444")]
    for i, (label, color) in enumerate(labels):
        cols[i].markdown(
            f"<span style='color:{color}; font-size:20px;'>●</span> {label}",
            unsafe_allow_html=True,
        )
