"""Tab 2: 안전 요약 - 카테고리별 안전 수준 카드 + 레이더 차트."""

import streamlit as st
import plotly.graph_objects as go
from config import SAFETY_CATEGORIES
from pipeline.db import load_csv
from pipeline.safety_scorer import (
    LocationInput, compute_safety_summaries, weighted_summary,
)
from dashboard.tabs.tab1_safety_map import geocode_district

CATEGORY_LABELS = {
    "traffic": ("교통 안전", "🚗"),
    "crime": ("생활 안전", "🔒"),
    "flood": ("자연재해", "🌊"),
    "air_quality": ("건강 환경", "🌬️"),
    "medical_access": ("의료 접근성", "🏥"),
    "fire": ("화재 안전", "🔥"),
}

LEVEL_KR = {"green": "양호", "yellow": "주의", "red": "경고"}
LEVEL_COLOR = {"green": "#22c55e", "yellow": "#eab308", "red": "#ef4444"}


def load_all_datasets():
    return {
        "traffic": load_csv("safety_traffic"),
        "crime": load_csv("safety_crime"),
        "flood": load_csv("safety_flood"),
        "air_quality": load_csv("safety_air_quality"),
        "medical_access": load_csv("safety_medical_access"),
        "fire": load_csv("safety_fire"),
    }


def render():
    if not st.session_state.get("profile_submitted"):
        st.info("왼쪽 프로필을 입력하고 '안전 체크 시작' 버튼을 눌러주세요.")
        return

    home = st.session_state.get("home_area", "강남구")
    work = st.session_state.get("work_area", "종로구")
    transport = st.session_state.get("transport_mode", "car")

    home_coords = geocode_district(home)
    work_coords = geocode_district(work)

    locations = [
        LocationInput("home", home_coords[0], home_coords[1], home),
        LocationInput("work", work_coords[0], work_coords[1], work),
    ]

    datasets = load_all_datasets()
    summaries = compute_safety_summaries(locations, datasets, transport)
    st.session_state["safety_summaries"] = summaries

    weighted = weighted_summary(summaries)

    # Radar chart
    categories = list(CATEGORY_LABELS.keys())
    labels = [CATEGORY_LABELS[c][1] + " " + CATEGORY_LABELS[c][0] for c in categories]
    scores = [100 - weighted.get(c, {}).get("score", 0) for c in categories]
    scores_closed = scores + [scores[0]]
    labels_closed = labels + [labels[0]]

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=scores_closed, theta=labels_closed,
        fill="toself",
        fillcolor="rgba(99, 102, 241, 0.2)",
        line=dict(color="#6366f1", width=2),
        name="안전 수준",
    ))
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
        showlegend=False, height=400,
        margin=dict(l=60, r=60, t=30, b=30),
    )
    st.plotly_chart(fig, use_container_width=True)

    # Category cards
    cols = st.columns(3)
    for i, cat in enumerate(categories):
        info = weighted.get(cat, {"level": "green", "score": 0})
        label, emoji = CATEGORY_LABELS[cat]
        level = info["level"]
        color = LEVEL_COLOR[level]
        level_text = LEVEL_KR[level]

        with cols[i % 3]:
            st.markdown(
                f"""
                <div style="border-left: 4px solid {color}; padding: 12px;
                            margin-bottom: 12px; background: rgba(0,0,0,0.02);
                            border-radius: 0 8px 8px 0;">
                    <div style="font-size: 14px; color: #999;">{emoji} {label}</div>
                    <div style="font-size: 24px; font-weight: bold; color: {color};">
                        {level_text}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    # Detail expander
    with st.expander("거주지·직장별 상세 내역"):
        for s in summaries:
            loc_label = {"home": "거주지", "work": "직장"}.get(s.location_type, s.location_type)
            label, emoji = CATEGORY_LABELS.get(s.category, (s.category, ""))
            color = LEVEL_COLOR.get(s.level, "#999")
            st.markdown(
                f"**{loc_label}** | {emoji} {label}: "
                f"<span style='color:{color}'>{LEVEL_KR.get(s.level, s.level)}</span> — {s.detail}",
                unsafe_allow_html=True,
            )

    # SHAP explanation
    st.divider()
    st.subheader("카테고리별 영향도 분석 (XGBoost + SHAP)")
    st.caption("각 안전 카테고리가 종합 안전 수준에 미치는 영향을 분석합니다")

    try:
        from pipeline.xgb_explainer import train_explainer, explain_district, get_shap_bar_data

        model, explainer, features_df = train_explainer(datasets)
        if model is not None:
            from pipeline.safety_scorer import match_district

            home_district, _ = match_district(*geocode_district(home))
            work_district, _ = match_district(*geocode_district(work))

            for loc_name, district in [("거주지", home_district), ("직장", work_district)]:
                explanation = explain_district(district, model, explainer, features_df)
                if explanation:
                    bar_data = get_shap_bar_data(explanation)
                    if bar_data:
                        names = [b[0] for b in bar_data]
                        values = [b[1] for b in bar_data]
                        colors = ["#ef4444" if v > 0 else "#22c55e" for v in values]

                        fig_shap = go.Figure(go.Bar(
                            x=values, y=names,
                            orientation="h",
                            marker_color=colors,
                        ))
                        fig_shap.update_layout(
                            title=f"{loc_name}: {district} 영향도",
                            xaxis_title="SHAP value (높을수록 위험 기여)",
                            height=250,
                            margin=dict(l=80, r=20, t=40, b=30),
                        )
                        st.plotly_chart(fig_shap, use_container_width=True)

            st.caption("빨간색: 위험도 증가 기여 / 초록색: 안전도 기여")
        else:
            st.info("데이터가 충분하지 않아 SHAP 분석을 건너뜁니다.")
    except Exception as e:
        st.info(f"SHAP 분석 모듈 로딩 중 오류: {e}")
