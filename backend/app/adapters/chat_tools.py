"""Tutor Chat 에이전트용 ToolExecutor.

컴포넌트 설계서 4.4절 결정 사항 반영: Tool의 스키마/의도는 에이전트 쪽 개념이지만
실제 저장소 조회 실행 주체는 API 서버(여기)다. LLM이 매 질문마다 별도로 tool-call을
왕복하게 하는 대신(레이턴시/게이트웨이 tool-calling 지원 불확실성 고려), WS 메시지를
받을 때마다 이 함수들로 필요한 컨텍스트(get_feedback + get_problem + get_model_answer
에 해당하는 정보)를 한 번에 로드해 에이전트 프롬프트에 얹는다.

`result_id`는 WS 연결 시점에 서버가 검증한 값만 사용한다 — 사용자가 채팅으로
임의의 식별자를 언급해도 그 값이 여기로 흘러들어오지 않는다 (호출부인
`app/api/chat.py`가 연결 시 확정한 result_id만 넘김).
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from backend.orm.models import AnalysisResults, AnalysisSessions, Problems, UserAnswers


class ChatToolError(ValueError):
    pass


@dataclass
class FeedbackContext:
    answer_id: str
    session_id: str
    user_id: str
    problem_title: str
    problem_content: str
    model_answer: str | None
    user_answer: str
    criteria_scores: list[dict] | None
    overall_comment: str | None
    corrections: dict | None


def load_feedback_context(db: Session, result_id: str) -> FeedbackContext:
    """get_feedback + get_problem_index + get_model_answer를 한 번에 수행."""
    result = db.get(AnalysisResults, result_id)
    if result is None:
        raise ChatToolError(f"채점 결과를 찾을 수 없습니다: {result_id}")

    answer = db.get(UserAnswers, result.answer_id)
    if answer is None:
        raise ChatToolError(f"학생 답안을 찾을 수 없습니다: {result.answer_id}")
    session = db.get(AnalysisSessions, answer.session_id)
    if session is None:
        raise ChatToolError(f"분석 세션을 찾을 수 없습니다: {answer.session_id}")
    problem = db.get(Problems, session.problem_id)
    if problem is None:
        raise ChatToolError(f"문제를 찾을 수 없습니다: {session.problem_id}")

    return FeedbackContext(
        answer_id=str(answer.id),
        session_id=str(session.id),
        user_id=str(session.user_id),
        problem_title=problem.title,
        problem_content=problem.content,
        model_answer=problem.model_answer,
        user_answer=answer.user_answer,
        criteria_scores=[score.model_dump() for score in result.criteria_scores],
        overall_comment=result.overall_comment,
        corrections=None,
    )


def format_context_for_prompt(ctx: FeedbackContext) -> str:
    scores_lines = []
    for c in ctx.criteria_scores or []:
        scores_lines.append(
            f"- {c.get('criterion')}: {c.get('score')}/{c.get('max_score', 5)}점"
            f" — 근거: {c.get('rationale', '')} / 개선방향: {c.get('improvement', '')}"
        )
    scores_text = "\n".join(scores_lines) or "(채점 항목 없음)"

    corrections_lines = []
    if ctx.corrections:
        for sc in ctx.corrections.get("spelling_corrections", []) or []:
            corrections_lines.append(
                f"- (맞춤법) '{sc.get('original')}' → '{sc.get('revised')}' ({sc.get('comment')})"
            )
        for ps in ctx.corrections.get("polish_suggestions", []) or []:
            corrections_lines.append(
                f"- (윤문) '{ps.get('original')}' → '{ps.get('suggestion')}' ({ps.get('reason')})"
            )
    corrections_text = "\n".join(corrections_lines) or "(첨삭 결과 없음)"

    return f"""[문제] {ctx.problem_title}
{ctx.problem_content}

[모범답안]
{ctx.model_answer or "(제공되지 않음)"}

[학생 답안]
{ctx.user_answer}

[채점 결과] (총평: {ctx.overall_comment or "(없음)"})
{scores_text}

[문법/표현 첨삭 결과]
{corrections_text}"""
