"""Tab 3: 예방 가이드 - 안전 가이드 + 리워드 미션 + 상담 체크리스트."""

import streamlit as st

from llm.guide_generator import (
    UserProfile,
    generate_rule_based_guide,
    generate_llm_guide,
)
from llm.backend import LLMRouter


def render():
    if not st.session_state.get("profile_submitted"):
        st.info("왼쪽 프로필을 입력하고 '안전 체크 시작' 버튼을 눌러주세요.")
        return

    summaries = st.session_state.get("safety_summaries", [])
    if not summaries:
        st.warning("'안전 요약' 탭을 먼저 확인해주세요.")
        return

    profile = UserProfile(
        home_area=st.session_state.get("home_area", ""),
        work_area=st.session_state.get("work_area", ""),
        transport_mode=st.session_state.get("transport_mode", "car"),
        age_group=st.session_state.get("age_group", "30s"),
        family_info=st.session_state.get("family_info", "1person"),
    )

    # ── A. 안전 & 예방 가이드 ──
    st.subheader("A. 안전 & 예방 가이드")

    col_rule, col_llm = st.columns(2)

    with col_rule:
        st.markdown("##### 기본 가이드")
        rule_guides = generate_rule_based_guide(profile, summaries)
        safety_guides = [g for g in rule_guides if g.guide_type == "safety"]
        if safety_guides:
            for g in safety_guides:
                st.markdown(f"- {g.content}")
        else:
            st.success("모든 안전 항목이 양호합니다.")

    with col_llm:
        st.markdown("##### AI 맞춤 가이드")
        if st.button("맞춤 가이드 생성", key="gen_llm_safety"):
            with st.spinner("프로필 기반 가이드 생성 중..."):
                try:
                    router = LLMRouter.from_config()
                    llm_guides = generate_llm_guide(profile, summaries, router)
                    safety_llm = [g for g in llm_guides if g.guide_type == "safety"]
                    if safety_llm:
                        for g in safety_llm:
                            st.markdown(g.content)
                        backend_name = {
                            "primary": "Ollama (로컬)",
                            "fallback": "Anthropic Haiku",
                        }.get(router.active_backend, router.active_backend)
                        st.caption(f"생성 엔진: {backend_name}")
                        st.session_state["llm_safety_output"] = safety_llm[0].content
                    else:
                        st.warning("LLM 연결을 확인해주세요. Ollama가 실행 중인지 확인하세요.")
                except Exception as e:
                    st.error(f"생성 오류: {e}")
        elif "llm_safety_output" in st.session_state:
            st.markdown(st.session_state["llm_safety_output"])

    # ── A/B 비교 평가 ──
    with st.expander("A/B 비교: 기본 가이드 vs AI 맞춤 가이드"):
        st.markdown("""
        **평가 기준**
        - 구체성: 실제 거주지/직장 지역과 이동수단을 반영하는가?
        - 실행 가능성: 바로 실천할 수 있을 만큼 구체적인가?
        - 톤: 불안감 없이 정보를 전달하는가?
        """)
        ab_rating = st.radio(
            "어떤 가이드가 더 도움이 됐나요?",
            ["기본 가이드", "AI 맞춤 가이드", "비슷함"],
            key="ab_rating",
            horizontal=True,
        )
        ab_reason = st.text_input("이유 (선택)", key="ab_reason")
        if st.button("평가 제출", key="ab_submit"):
            st.success("평가가 기록되었습니다.")

    st.divider()

    # ── B. 리워드 미션 ──
    st.subheader("B. 리워드 미션")
    st.caption("예방 행동을 실천하고 포인트를 적립하세요")

    reward_guides = [g for g in rule_guides if g.guide_type == "reward"]
    if reward_guides:
        for g in reward_guides:
            parts = g.content.split(" → ")
            mission = parts[0] if parts else g.content
            points = parts[1] if len(parts) > 1 else ""

            st.markdown(
                f"""
                <div style="display:flex; justify-content:space-between;
                            align-items:center; padding:10px 16px;
                            margin-bottom:8px; background:#f8fafc;
                            border-radius:8px; border:1px solid #e2e8f0;">
                    <span>{mission}</span>
                    <span style="background:#6366f1; color:white;
                                 padding:4px 12px; border-radius:12px;
                                 font-weight:bold; font-size:13px;">{points}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
    else:
        st.info("추천 미션이 없습니다.")

    # ── B-2. 레벨 & 뱃지 ──
    st.markdown("")
    total_possible = sum(
        int(g.content.split("→")[-1].strip().replace("P", ""))
        for g in reward_guides
        if "→" in g.content
    ) if reward_guides else 0

    # Simulate completion (demo mode)
    if "completed_missions" not in st.session_state:
        st.session_state["completed_missions"] = 0

    completed = st.session_state["completed_missions"]
    earned = min(completed * 100, total_possible)

    # Level thresholds
    levels = [
        (0, "안전 입문자", "🌱"),
        (200, "안전 실천러", "🛡️"),
        (500, "안전 매니저", "⭐"),
        (1000, "안전 마스터", "🏆"),
    ]

    current_level = levels[0]
    next_level = levels[1] if len(levels) > 1 else None
    for i, (threshold, name, icon) in enumerate(levels):
        if earned >= threshold:
            current_level = (threshold, name, icon)
            next_level = levels[i + 1] if i + 1 < len(levels) else None

    level_name = current_level[1]
    level_icon = current_level[2]

    if next_level:
        next_threshold = next_level[0]
        progress = min(earned / next_threshold, 1.0) if next_threshold > 0 else 1.0
        progress_pct = int(progress * 100)
        next_msg = f"다음 레벨 '{next_level[1]}' 까지 {next_threshold - earned}P"
    else:
        progress_pct = 100
        next_msg = "최고 레벨 달성!"

    st.markdown(
        f"""
        <div style="padding:12px 16px; background:#f8fafc;
                    border-radius:10px; border:1px solid #e2e8f0; margin-bottom:8px;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                <div>
                    <span style="font-size:20px;">{level_icon}</span>
                    <span style="font-size:15px; font-weight:500; margin-left:6px;">{level_name}</span>
                </div>
                <span style="font-size:13px; color:#666;">{earned}P 적립</span>
            </div>
            <div style="background:#e2e8f0; border-radius:6px; height:8px; overflow:hidden;">
                <div style="background:#A3D043; height:100%; width:{progress_pct}%; border-radius:6px;"></div>
            </div>
            <div style="font-size:11px; color:#999; margin-top:4px;">{next_msg}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.divider()

    # ── C. 상담 전 체크리스트 ──
    st.subheader("C. 보장 점검 체크리스트")
    st.caption("설계사 상담 전 확인하면 좋은 항목입니다")

    alert_cats = [s for s in summaries if s.level in ("red", "yellow")]
    # Deduplicate by category
    seen = set()
    unique_alerts = []
    for s in alert_cats:
        if s.category not in seen:
            seen.add(s.category)
            unique_alerts.append(s)

    if unique_alerts:
        for s in unique_alerts[:3]:
            cat_kr = {
                "traffic": "교통사고", "crime": "생활안전",
                "flood": "자연재해", "air_quality": "건강·환경",
                "medical_access": "의료접근성", "fire": "화재",
            }.get(s.category, s.category)
            st.checkbox(
                f"{cat_kr} 관련 보장 상태를 설계사에게 확인해보세요",
                key=f"check_{s.category}",
            )
    else:
        st.success("현재 모든 항목이 양호합니다.")

    st.caption("최종 판단은 담당 설계사와 상담 후 결정해주세요.")
