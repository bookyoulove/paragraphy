import json
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from .bareun_client import check_spelling
from .llm_client import ClaudeClient
from .models import AnalysisSession, ChatMessage, Problem
from .rubrics import NIKL_CRITERIA
from .tool_executor import TOOLS, ToolExecutor

GRADING_OUTPUT_SPEC = """
반드시 아래 JSON 형식으로만 답하라 (다른 텍스트, 설명, 코드펜스 없이 JSON 객체 하나만):
{
  "scores": [{"label": "준거명", "value": 정수, "max_score": 정수}, ...],
  "commentary": "총평 2문장 이내",
  "suggestions": ["수정 방향 1", "수정 방향 2", "수정 방향 3"],
  "grammar_errors": [
    {"type": "어색한 표현|논리 비약|중복 표현 등 분류", "before": "답안 원문에 실제로 등장하는 부분 문자열", "after": "수정 제안", "note": "근거 설명"}
  ]
}
- "before" 값은 반드시 학생 답안 원문에 그대로 등장하는 부분 문자열이어야 한다 (하이라이트 표시에 사용됨).
- 매우 중요: grammar_errors에는 띄어쓰기·맞춤법·표준어 등 어문 규정 오류를 포함하지 말 것 (별도의 맞춤법 검사 시스템이 이미 전담한다). 여기서는 논리 비약, 어색한 표현, 불필요한 반복 등 내용·문장 수준의 문제만 최대 3개까지 포함한다.
- 매우 중요: 모든 문자열 값 내부에서는 큰따옴표(")를 사용하지 말 것. 원문이나 예시를 인용할 때는 작은따옴표(') 또는 「」를 사용하라. JSON 이스케이프 오류를 방지하기 위함이다.
"""


def _grading_system_prompt(problem: Optional[Problem]) -> str:
    source = problem.source if problem else "일반"
    base = (
        "당신은 한국 대입 논술·국어 논증적 글쓰기를 채점하는 전문 채점관(Grading Agent)입니다.\n"
        "채점은 반드시 아래에 주어진 '문제 출처별 채점 기준'만 근거로 삼아야 하며, "
        "다른 대학/기관의 일반적인 채점 관행을 임의로 섞어서는 안 됩니다.\n"
    )

    if problem is None:
        return base + "채점 기준이 제공되지 않았습니다. 논리성/구성/표현/맞춤법을 기준으로 100점 만점으로 채점하십시오.\n" + GRADING_OUTPUT_SPEC

    if source == "국립국어원":
        criteria_lines = "\n".join(f"- {c['label']} (1~5점)" for c in NIKL_CRITERIA)
        return (
            base
            + f"[문제]\n{problem.content}\n\n"
            + f"[채점 준거 — 국립국어원 논증적 글쓰기 기준, 반드시 이 9개 준거만 사용]\n{problem.rubric}\n\n"
            + "scores 배열은 반드시 아래 9개 준거를 이 순서 그대로, label을 정확히 동일하게 사용하고 "
              f"각 value는 1~5, max_score는 5로 채점하라:\n{criteria_lines}\n\n"
            + GRADING_OUTPUT_SPEC
        )

    # 대학 논술(한양대/경희대 등)은 문서화된 공식 채점기준표를, 사용자입력 문제는 Rubric Agent가
    # 생성해 사용자가 확정한 채점기준을 그대로 근거로 사용한다.
    rubric_label = "공식 채점기준 및 배점표" if source != "사용자입력" else "사용자가 확정한 채점기준"
    model_answer_block = f"\n\n[모범답안 예시]\n{problem.model_answer}" if problem.model_answer else ""
    return (
        base
        + f"[문제 및 제시문]\n{problem.content}\n\n"
        + f"[채점 기준 — {source} {rubric_label}, 이 기준의 항목/배점을 그대로 scores 배열로 반영할 것]\n{problem.rubric}"
        + model_answer_block
        + "\n\n"
        + GRADING_OUTPUT_SPEC
    )


def _normalize_grading_result(data: Dict[str, Any]) -> Dict[str, Any]:
    scores = data.get("scores") or []
    normalized_scores = []
    total_value, total_max = 0, 0
    for item in scores:
        try:
            value = int(item.get("value", 0))
            max_score = int(item.get("max_score", item.get("max", 0)) or 0)
        except (TypeError, ValueError):
            continue
        label = str(item.get("label", "")).strip() or "항목"
        normalized_scores.append({"label": label, "value": value, "max_score": max_score})
        total_value += value
        total_max += max_score

    grammar_errors = data.get("grammar_errors") or []
    normalized_errors = []
    for err in grammar_errors[:5]:
        if not isinstance(err, dict):
            continue
        normalized_errors.append(
            {
                "type": str(err.get("type", "표현")),
                "before": str(err.get("before", "")),
                "after": str(err.get("after", "")),
                "note": str(err.get("note", "")),
            }
        )

    suggestions = [str(s) for s in (data.get("suggestions") or [])][:5]

    return {
        "score": total_value,
        "total_max": total_max or 100,
        "scores": normalized_scores,
        "commentary": data.get("commentary") or "",
        "suggestions": suggestions,
        "grammar_errors": normalized_errors,
    }


async def grade_answer(db: Session, session: AnalysisSession, text: str) -> Dict[str, Any]:
    problem = db.query(Problem).filter(Problem.id == session.problem_id).first()
    client = ClaudeClient()
    system = _grading_system_prompt(problem)
    user = f"[학생 답안]\n{text}"
    data = await client.complete_json(system, user, max_tokens=2200)
    result = _normalize_grading_result(data)

    # 어문 규정 검사는 출처와 무관하게 공통으로 Bareun이 담당 (설계 원칙)
    bareun_errors = check_spelling(text)
    result["grammar_errors"] = (bareun_errors + result["grammar_errors"])[:8]
    return result


RUBRIC_AGENT_SYSTEM_PROMPT = (
    "당신은 대입 논술 채점 기준을 설계하는 Rubric Agent입니다. 사용자가 직접 입력한 논술 문제를 "
    "분석하여, 채점 위원이 그대로 사용할 수 있는 구체적인 채점 기준표를 한국어로 작성하십시오.\n"
    "규칙:\n"
    "1. 채점 항목은 3~6개로 나누고, 각 항목의 배점 합계가 정확히 100점이 되도록 하십시오.\n"
    "2. 각 항목마다 '항목명 (배점점) — 무엇을 평가하는지 1~2문장 설명' 형식으로 작성하십시오.\n"
    "3. 문제에 제시문·지문이 있다면 그 내용을 반영해 항목을 구체화하십시오.\n"
    "4. 다른 설명, 인사말, 코드펜스 없이 채점 기준표 텍스트만 출력하십시오."
)


async def generate_rubric(content: str, title: Optional[str] = None, hint: Optional[str] = None) -> str:
    client = ClaudeClient()
    user_parts = []
    if title:
        user_parts.append(f"[문제 제목]\n{title}")
    user_parts.append(f"[문제 및 지문]\n{content}")
    if hint:
        user_parts.append(f"[사용자가 참고를 요청한 사항]\n{hint}")
    messages = [
        {"role": "system", "content": RUBRIC_AGENT_SYSTEM_PROMPT},
        {"role": "user", "content": "\n\n".join(user_parts)},
    ]
    reply = await client.chat(messages, max_tokens=1200)
    return (reply.content or "").strip()


TUTOR_SYSTEM_PROMPT = (
    "당신은 학생의 논술 답안 채점 결과를 바탕으로 질문에 답하는 Tutor Chat 에이전트입니다.\n"
    "직접 DB나 채점 로직에 접근할 수 없으므로, 필요한 정보는 반드시 제공된 도구(get_feedback, "
    "get_problem_index, get_model_answer)를 호출해서만 확인하십시오. 도구를 호출하지 않고 임의로 "
    "점수나 오류를 추측해서 답하지 마십시오. 답변은 한국어로, 3~4문장 이내로 간결하게 하십시오."
)


async def chat_agent_reply(db: Session, session: AnalysisSession, history: List[ChatMessage]) -> str:
    client = ClaudeClient()
    executor = ToolExecutor(db, session)

    messages: List[Dict[str, Any]] = [{"role": "system", "content": TUTOR_SYSTEM_PROMPT}]
    for msg in history:
        role = "assistant" if msg.role == "assistant" else "user"
        messages.append({"role": role, "content": msg.text})

    for _ in range(3):
        reply = await client.chat(messages, tools=TOOLS, max_tokens=700)
        tool_calls = getattr(reply, "tool_calls", None)
        if tool_calls:
            messages.append(
                {
                    "role": "assistant",
                    "content": reply.content,
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                        }
                        for tc in tool_calls
                    ],
                }
            )
            for tc in tool_calls:
                try:
                    args = json.loads(tc.function.arguments or "{}")
                except json.JSONDecodeError:
                    args = {}
                result = executor.call(tc.function.name, args)
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": json.dumps(result, ensure_ascii=False),
                    }
                )
            continue
        return reply.content or "답변을 생성하지 못했습니다."

    return "죄송합니다, 지금은 답변을 완성하지 못했습니다. 다시 질문해 주세요."
