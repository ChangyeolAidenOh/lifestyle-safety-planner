"""Safety guide generator: rule-based baseline + LLM personalization.

Produces both outputs for A/B comparison in dashboard.
"""

import logging
from dataclasses import dataclass, field

from llm.backend import LLMRouter
from llm.prompts import (
    SYSTEM_PROMPT,
    SAFETY_GUIDE_PROMPT,
    REWARD_MISSION_PROMPT,
)

logger = logging.getLogger(__name__)


@dataclass
class UserProfile:
    """User input for safety profile generation."""
    home_area: str = ""
    work_area: str = ""
    transport_mode: str = "car"
    age_group: str = "30s"
    family_info: str = "1person"


@dataclass
class SafetySummary:
    """Aggregated safety information per category."""
    category: str = ""
    level: str = "green"         # green / yellow / red
    score: float = 0.0
    detail: str = ""
    location_type: str = "home"  # home / work / commute


@dataclass
class GuideOutput:
    """Container for guide output with source tracking."""
    content: str = ""
    source: str = "rule_based"   # rule_based / llm
    guide_type: str = "safety"   # safety / reward / consultation


# ================================================================
# Rule-based guide templates
# ================================================================

RULE_TEMPLATES = {
    "traffic": {
        "red": "출퇴근 경로 내 교통사고 다발지역이 있습니다. 보행 시 각별히 주의하세요.",
        "yellow": "교통 관련 주의가 필요한 구간이 일부 있습니다.",
        "green": "교통 안전 수준이 양호합니다.",
    },
    "crime": {
        "red": "생활권 내 범죄 발생 빈도가 높은 지역이 있습니다. 야간 이동 시 주의하세요.",
        "yellow": "일부 지역에서 범죄 주의가 필요합니다.",
        "green": "생활 안전 수준이 양호합니다.",
    },
    "flood": {
        "red": "침수 이력이 있는 구역이 인접해 있습니다. 장마철 대비를 권장합니다.",
        "yellow": "침수 주의 지역이 일부 있습니다.",
        "green": "자연재해 안전 수준이 양호합니다.",
    },
    "air_quality": {
        "red": "대기질이 자주 '나쁨' 이상인 지역입니다. 실외 활동 시 마스크 착용을 권장합니다.",
        "yellow": "대기질 변동이 있는 지역입니다. 미세먼지 예보를 확인하세요.",
        "green": "대기질 수준이 양호합니다.",
    },
    "medical_access": {
        "red": "주변 의료기관 밀도가 낮습니다. 가까운 응급실 위치를 미리 확인하세요.",
        "yellow": "의료기관이 다소 멀리 위치해 있습니다.",
        "green": "의료 접근성이 양호합니다.",
    },
    "fire": {
        "red": "화재 발생 빈도가 높은 지역입니다. 소화기와 대피 경로를 확인하세요.",
        "yellow": "화재 주의가 필요한 구역이 있습니다.",
        "green": "화재 안전 수준이 양호합니다.",
    },
}

REWARD_TEMPLATES = {
    "traffic": [
        {"mission": "안전운전 주간 체크리스트 완료", "points": 100},
        {"mission": "야간 안전경로 공유 인증", "points": 50},
        {"mission": "대중교통 이용 5회 인증", "points": 200},
    ],
    "air_quality": [
        {"mission": "건강검진 예약 인증", "points": 500},
        {"mission": "미세먼지 나쁨 시 실내 운동 인증", "points": 30},
    ],
    "medical_access": [
        {"mission": "가까운 병원/응급실 즐겨찾기 등록", "points": 50},
    ],
    "general": [
        {"mission": "가족 생활안전 체크리스트 완료", "points": 100},
        {"mission": "가족 응급 연락처 등록", "points": 50},
    ],
}


def generate_rule_based_guide(profile, summaries):
    """Generate guide using rule-based templates.

    Deduplicates by category: takes worst level across locations.

    Returns:
        list[GuideOutput]
    """
    outputs = []

    # Deduplicate: pick worst level per category
    cat_worst = {}
    for s in summaries:
        if s.level not in ("red", "yellow"):
            continue
        rank = {"red": 0, "yellow": 1}
        if s.category not in cat_worst or rank.get(s.level, 2) < rank.get(cat_worst[s.category].level, 2):
            cat_worst[s.category] = s

    # Sort by severity and pick top 3
    alert_cats = sorted(
        cat_worst.values(),
        key=lambda s: {"red": 0, "yellow": 1}.get(s.level, 2),
    )[:3]

    for s in alert_cats:
        template = RULE_TEMPLATES.get(s.category, {}).get(s.level, "")
        if template:
            outputs.append(GuideOutput(
                content=template,
                source="rule_based",
                guide_type="safety",
            ))

    # Reward missions
    for s in alert_cats:
        missions = REWARD_TEMPLATES.get(s.category, [])
        for m in missions:
            outputs.append(GuideOutput(
                content=f"{m['mission']} → {m['points']}P",
                source="rule_based",
                guide_type="reward",
            ))

    # Always include general missions
    for m in REWARD_TEMPLATES["general"]:
        outputs.append(GuideOutput(
            content=f"{m['mission']} → {m['points']}P",
            source="rule_based",
            guide_type="reward",
        ))

    return outputs


def generate_llm_guide(profile, summaries, router=None):
    """Generate personalized guide using LLM.

    Only sends non-green (alert/caution) items to reduce tokens.

    Returns:
        list[GuideOutput] or empty list if LLM unavailable.
    """
    if router is None:
        router = LLMRouter.from_config()

    # Build compact safety summary - only non-green items
    level_kr = {"green": "양호", "yellow": "주의", "red": "경고"}
    summary_lines = []
    for s in summaries:
        if s.level == "green":
            continue
        summary_lines.append(
            f"- {s.category} ({s.location_type}): {level_kr.get(s.level, '')} | {s.detail}"
        )

    if not summary_lines:
        summary_lines.append("- 모든 카테고리 양호")

    safety_text = "\n".join(summary_lines)

    prompt = SAFETY_GUIDE_PROMPT.format(
        age_group=profile.age_group,
        home_area=profile.home_area,
        work_area=profile.work_area,
        transport_mode=profile.transport_mode,
        safety_summary=safety_text,
    )

    result = router.generate(prompt, system=SYSTEM_PROMPT, max_tokens=300)
    outputs = []

    if result:
        outputs.append(GuideOutput(
            content=result,
            source="llm",
            guide_type="safety",
        ))
        logger.info("LLM guide generated via %s backend.", router.active_backend)
    else:
        logger.warning("LLM generation failed; returning empty.")

    # Generate reward mission descriptions
    alert_cats = [s.category for s in summaries if s.level in ("red", "yellow")]
    mission_lines = []
    for cat in alert_cats[:3]:
        for m in REWARD_TEMPLATES.get(cat, []):
            mission_lines.append(f"- {m['mission']} ({m['points']}P)")

    if mission_lines:
        reward_prompt = REWARD_MISSION_PROMPT.format(
            age_group=profile.age_group,
            transport_mode=profile.transport_mode,
            alert_categories=", ".join(alert_cats[:3]),
            mission_list="\n".join(mission_lines),
        )
        reward_result = router.generate(reward_prompt, system=SYSTEM_PROMPT)
        if reward_result:
            outputs.append(GuideOutput(
                content=reward_result,
                source="llm",
                guide_type="reward",
            ))

    return outputs


def generate_guide_ab(profile, summaries, router=None):
    """Generate both rule-based and LLM guides for A/B comparison.

    Returns:
        dict with keys 'rule_based' and 'llm', each a list of GuideOutput.
    """
    rule_outputs = generate_rule_based_guide(profile, summaries)
    llm_outputs = generate_llm_guide(profile, summaries, router)

    return {
        "rule_based": rule_outputs,
        "llm": llm_outputs,
    }
