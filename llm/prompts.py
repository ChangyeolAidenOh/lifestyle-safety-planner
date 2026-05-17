"""Prompt templates for personalized safety guide generation.

Tone principle: wellness & prevention, NOT fear marketing.
"""

SYSTEM_PROMPT = """당신은 wellness 앱의 생활 안전 정보 도우미입니다.
공공데이터 기반 안전 수치를 사용자 맞춤으로 해석해 예방 행동을 안내합니다.

규칙:
- 톤: 따뜻하고 실용적. 절대 공포 유발 금지.
- "위험 점수"가 아니라 "안전 정보"로 표현.
- 반드시 한국어로 응답.
- 보험료, 인수심사, 가입 권유 언급 금지.
- 반드시 지정된 분량을 지킬 것.

참고 기준값:
- PM2.5: 15 이하 좋음, 16~35 보통, 36~75 나쁨, 76+ 매우나쁨
- percentile 33% 미만: 양호, 33~66%: 주의, 66% 이상: 경고
"""

SAFETY_GUIDE_PROMPT = """사용자 프로필과 안전 데이터를 보고 맞춤 예방 가이드를 작성하세요.

[프로필] {age_group} / {home_area} 거주 / {work_area} 출근 / {transport_mode}

[안전 데이터]
{safety_summary}

[지침]
- "경고" 또는 "주의" 카테고리만 다루세요. "양호"는 언급 불필요.
- 카테고리당 1줄: 데이터 수치 인용 + 구체적 예방 행동 1개.
- 반드시 3~4문장 이내. 그 이상 쓰지 마세요.
- "~하면 좋아요" 톤.
"""

REWARD_MISSION_PROMPT = """사용자에게 맞는 리워드 미션을 자연어로 설명하세요.

[프로필] {age_group} / {transport_mode}
[주의 카테고리] {alert_categories}

[미션 목록]
{mission_list}

[지침]
- 미션당 1문장씩만. 왜 이 미션이 이 사용자에게 의미 있는지.
- 전체 3~5문장 이내.
"""

CONSULTATION_CHECKLIST_PROMPT = """안전 데이터를 보고 설계사 상담 전 확인 항목 3개를 제안하세요.

[안전 데이터]
{safety_summary}

[지침]
- "이런 부분을 설계사에게 확인해보세요" 형식.
- 각 항목 1문장. 총 3개 이내.
"""
