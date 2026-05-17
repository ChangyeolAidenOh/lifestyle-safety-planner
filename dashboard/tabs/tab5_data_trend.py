"""Tab 5: 데이터 & 트렌드 - 데이터 출처, 갱신 주기, 트렌드."""

import streamlit as st
import plotly.express as px
import pandas as pd

from pipeline.db import load_csv


def render():
    st.subheader("데이터 출처")
    sources = pd.DataFrame([
        {"카테고리": "교통", "출처": "도로교통공단 (TAAS)",
         "URL": "taas.koroad.or.kr", "갱신 주기": "연간", "형식": "CSV/API"},
        {"카테고리": "범죄", "출처": "경찰청",
         "URL": "data.go.kr", "갱신 주기": "연간", "형식": "CSV"},
        {"카테고리": "침수", "출처": "서울시 열린데이터",
         "URL": "data.seoul.go.kr", "갱신 주기": "수시", "형식": "CSV"},
        {"카테고리": "의료", "출처": "건강보험심사평가원",
         "URL": "opendata.hira.or.kr", "갱신 주기": "월간", "형식": "API"},
        {"카테고리": "대기질", "출처": "에어코리아",
         "URL": "airkorea.or.kr", "갱신 주기": "시간", "형식": "API"},
        {"카테고리": "화재", "출처": "소방청",
         "URL": "nfa.go.kr", "갱신 주기": "연간", "형식": "CSV"},
    ])
    st.dataframe(sources, use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("트렌드")

    trend_cat = st.selectbox(
        "카테고리",
        ["교통사고", "범죄", "화재", "대기질"],
        key="trend_category",
    )

    if trend_cat == "교통사고":
        df = load_csv("safety_traffic")
        if not df.empty and "year" in df.columns:
            yearly = df.groupby("year")["accident_count"].sum().reset_index()
            fig = px.bar(yearly, x="year", y="accident_count",
                         title="연도별 교통사고 건수",
                         labels={"accident_count": "사고 건수", "year": "연도"})
            st.plotly_chart(fig, use_container_width=True)

    elif trend_cat == "범죄":
        df = load_csv("safety_crime")
        if not df.empty and "year" in df.columns:
            yearly = df.groupby(["year", "crime_type"])["occurrence"].sum().reset_index()
            fig = px.bar(yearly, x="year", y="occurrence", color="crime_type",
                         title="연도별·유형별 범죄 발생 건수",
                         labels={"occurrence": "건수", "year": "연도", "crime_type": "유형"})
            st.plotly_chart(fig, use_container_width=True)

    elif trend_cat == "화재":
        df = load_csv("safety_fire")
        if not df.empty and "year" in df.columns:
            yearly = df.groupby("year")["fire_count"].sum().reset_index()
            fig = px.bar(yearly, x="year", y="fire_count",
                         title="연도별 화재 건수",
                         labels={"fire_count": "화재 건수", "year": "연도"})
            st.plotly_chart(fig, use_container_width=True)

    elif trend_cat == "대기질":
        df = load_csv("safety_air_quality")
        if not df.empty and "measure_date" in df.columns:
            df["measure_date"] = pd.to_datetime(df["measure_date"])
            df["month"] = df["measure_date"].dt.to_period("M").astype(str)
            monthly = df.groupby("month")["pm25"].mean().reset_index()
            fig = px.line(monthly, x="month", y="pm25",
                          title="월별 평균 PM2.5 추이",
                          labels={"pm25": "PM2.5 (ug/m3)", "month": "월"})
            fig.add_hline(y=15, line_dash="dash", line_color="green",
                          annotation_text="WHO 권고 기준")
            fig.add_hline(y=35, line_dash="dash", line_color="orange",
                          annotation_text="환경부 '나쁨' 기준")
            st.plotly_chart(fig, use_container_width=True)

    st.divider()
    st.subheader("산출 방법")
    st.markdown("""
    **안전 수준 산출:**
    1. 사용자 위치(거주지, 직장)에서 가장 가까운 구(자치구)를 매칭합니다.
    2. 해당 구의 카테고리별 수치를 서울시 전체 구 분포 대비 백분위로 환산합니다.
    3. 거주지 50% + 직장 30% + 출퇴근 15% + 기타 5% 가중 평균을 적용합니다.
    4. 수준 판정: 양호 (하위 33%), 주의 (33~66%), 경고 (상위 33%).

    **AI 맞춤 가이드:**
    - 1차: Ollama (Qwen 2.5 7B) 로컬 추론 — API 비용 없음
    - 2차: Anthropic Haiku — 클라우드 fallback
    - 기본 가이드와 AI 맞춤 가이드의 구체성·실행 가능성을 A/B 비교합니다.
    """)
