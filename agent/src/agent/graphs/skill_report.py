"""Generate a weekly report from persisted, per-answer grading evidence."""

from __future__ import annotations

import logging
import re
from typing import Any

from langchain_core.messages import HumanMessage
from langgraph.graph import END, START, StateGraph
from shared.schema.skill_report import WeeklySkillReportOutput

from agent.model import get_structured_model
from agent.schemas.skill_report import SkillReportState

MAX_ATTEMPTS = 3
logger = logging.getLogger(__name__)

SKILLS: tuple[tuple[str, str], ...] = (
    ("claim", "주장"),
    ("evidence_relevance", "이유·근거의 적절성"),
    ("evidence_sufficiency", "이유·근거의 충분성"),
    ("counterargument", "다른 입장에 대한 고려"),
    ("passage_summary", "지문 요약"),
)


def _build_prompt(state: SkillReportState) -> str:
    reviews = state.request.model_dump_json(indent=2)
    skill_list = "\n".join(f"- {key}: {label}" for key, label in SKILLS)
    return f"""너는 학생의 최근 논술 채점 이력을 분석하는 학습 코치다.
아래는 DB에 저장된 최근 7일간의 채점 항목별 점수, 채점 근거(rationale), 개선 의견,
그리고 총평이다. 제공된 데이터만 근거로 주간 학습 리포트를 작성하라.

반드시 아래 5개 역량을 각각 한 번씩, 0~5점 정수로 평가하라.
{skill_list}

평가 원칙:
- 문제별 루브릭의 명칭이 다르더라도 의미와 채점 리뷰를 종합해 공통 역량으로 판단한다.
- 근거가 약한 항목은 이유를 rationale에 명시하되, 점수를 임의로 높게 주지 마라.
- rationale은 반드시 "강점: ... 보완점: ..." 형식으로 작성한다. 최근 답안들에서
  잘 수행한 역량과 보완할 역량을 일반적인 학습 언어로 각각 1문장씩 설명한다.
- [가], [나], 제시문 번호, 특정 문제 제목·세부 내용처럼 이 리포트만 읽어서는 이해할 수
  없는 내부 표기를 절대 사용하지 마라. 원본 리뷰를 그대로 인용하지 말고, 주장·근거·
  요약의 완결성처럼 사용자가 이해할 수 있는 학습 역량 언어로 바꿔 설명한다.
- 특히 "[가]·[다]의 핵심을 요약했다"처럼 쓰지 마라. 반드시 "각 지시문의 핵심을
  자신의 언어로 요약했다"처럼, 문제를 보지 않아도 이해되는 일반화된 문장으로 바꿔라.
- "[나]를 누락했다"는 "일부 지시문의 핵심이 빠져 요약의 완결성이 떨어졌다"로 바꿔라.
- improvement는 특정 문제에만 적용되는 지시가 아니라, 다음 답안부터 반복 적용할 수 있는
  구체적인 행동 한 가지로 작성한다.
- overall_skill_comment, next_learning_goal, recommended_actions 역시 데이터에 근거하며,
  완성 답안을 대신 작성하지 않는다.
- skill_scores의 key는 위 목록의 영문 key를 정확히 사용하고, 5개 모두 포함한다.

채점 데이터(JSON):
{reviews}"""


def _normalise_report(output: WeeklySkillReportOutput) -> WeeklySkillReportOutput:
    expected_keys = [key for key, _ in SKILLS]
    output_by_key = {item.key: item for item in output.skill_scores}
    if len(output_by_key) != len(output.skill_scores) or set(output_by_key) != set(
        expected_keys
    ):
        raise ValueError(
            "skill_scores must contain each of the five fixed skill keys once."
        )
    if re.search(r"\[[가-힣]\]", output.model_dump_json()):
        raise ValueError(
            "리포트에 [가], [나] 같은 문제 내부 표기가 남아 있습니다. "
            "문제를 보지 않아도 이해되는 일반적인 학습 언어로 바꾸세요."
        )
    return output.model_copy(
        update={"skill_scores": [output_by_key[key] for key in expected_keys]}
    )


def skill_report_agent_node(state: SkillReportState) -> dict[str, Any]:
    base_prompt = _build_prompt(state)
    last_error = ""
    for attempt in range(1, MAX_ATTEMPTS + 1):
        prompt = base_prompt
        if attempt > 1:
            prompt += f"\n\n이전 구조화 출력 오류: {last_error}. 형식을 바로잡아 다시 작성하라."
        try:
            output = get_structured_model(WeeklySkillReportOutput).invoke(
                [HumanMessage(content=prompt)]
            )
            return {"report": _normalise_report(output), "error": None}
        except Exception as exc:
            logger.exception("Skill report model attempt %d failed", attempt)
            last_error = str(exc)
    return {"error": f"주간 리포트 생성이 {MAX_ATTEMPTS}회 실패했습니다: {last_error}"}


def build_skill_report_graph():
    graph = StateGraph(SkillReportState)
    graph.add_node("skill_report_agent", skill_report_agent_node)
    graph.add_edge(START, "skill_report_agent")
    graph.add_edge("skill_report_agent", END)
    return graph.compile()


skill_report_app = build_skill_report_graph()
