"""Lifestyle Safety & Reward Planner - Streamlit Dashboard."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

st.set_page_config(
    page_title="내 생활권 안전 체크",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Sidebar
st.sidebar.title("내 프로필")
home_area = st.sidebar.text_input("거주지", value="강남구", key="home_area")
work_area = st.sidebar.text_input("직장 소재지", value="종로구", key="work_area")
transport_mode = st.sidebar.selectbox(
    "주 이동수단",
    ["car", "subway", "bus", "walk", "bicycle"],
    format_func=lambda x: {
        "car": "자가용", "subway": "지하철", "bus": "버스",
        "walk": "도보", "bicycle": "자전거",
    }[x],
    index=0,
    key="transport_mode",
)
age_group = st.sidebar.selectbox(
    "연령대",
    ["20s", "30s", "40s", "50s", "60+"],
    format_func=lambda x: {
        "20s": "20대", "30s": "30대", "40s": "40대",
        "50s": "50대", "60+": "60대 이상",
    }[x],
    index=1,
    key="age_group",
)
family_info = st.sidebar.selectbox(
    "가구 유형",
    ["1person", "couple", "family_with_kids", "family_with_parents"],
    format_func=lambda x: {
        "1person": "1인 가구", "couple": "부부",
        "family_with_kids": "자녀 동반", "family_with_parents": "부모 동거",
    }[x],
    index=0,
    key="family_info",
)

run_btn = st.sidebar.button("안전 체크 시작", type="primary", use_container_width=True)

if run_btn:
    st.session_state["profile_submitted"] = True

st.title("내 생활권 안전 체크")
st.caption("공공데이터 기반 생활 동선 안전 정보 서비스")

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🗺️ 안전 지도",
    "📊 안전 요약",
    "📋 예방 가이드",
    "🔍 지역 탐색",
    "📈 데이터 & 트렌드",
])

with tab1:
    from dashboard.tabs.tab1_safety_map import render
    render()

with tab2:
    from dashboard.tabs.tab2_safety_summary import render
    render()

with tab3:
    from dashboard.tabs.tab3_action_guide import render
    render()

with tab4:
    from dashboard.tabs.tab4_safety_explorer import render
    render()

with tab5:
    from dashboard.tabs.tab5_data_trend import render
    render()
