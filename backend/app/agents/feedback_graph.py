"""LangGraph 기반 문법/표현 첨삭 에이전트.

그래프 구조:

    START -> guardrail_input -> (유해 콘텐츠면) END
                              -> spelling_agent -> polish_agent -> END

- guardrail_input: 원문에 실제 유해 콘텐츠가 있는지 검사(grading_graph와 동일 기준).
  걸리면 맞춤법 검사·LLM 호출 없이 즉시 종료.
- spelling_agent: bareun.ai(`spelling_service.check_spelling`)로 맞춤법/띄어쓰기 교정.
  bareun 호출이 실패해도(키 미설정, API 장애 등) 전체 파이프라인을 막지 않고
  교정 없이 다음 단계로 넘어간다 (에이전트 실패 시 폴백 처리).
- polish_agent: 맞춤법 교정과는 별개로, 어색하거나 논증에 비효과적인 표현을 다듬는
  "윤문 제안"을 LLM으로 생성한다. 벡터DB(3단계 RAG)에서 "문장과 어휘"/"어문 규범과
  관습" 관련 채점 기준 해설을 검색해 근거로 함께 제공한다.
"""

from __future__ import annotations

import json
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from app.agents.common import extract_json
from app.services import guardrail_service, vector_store
from app.services.llm_client import LLMClientError, chat_completion
from app.services.spelling_service import SpellingServiceError, check_spelling

MAX_ATTEMPTS = 3
RAG_QUERY = "문장과 어휘 표현이 자연스럽고 논증에 효과적인가, 어문 규범과 글쓰기 관습을 지키는가"
RAG_TOP_K = 3


class SpellingCorrection(TypedDict):
    original: str
    revised: str
    category: str
    comment: str


class PolishSuggestion(TypedDict):
    original: str
    suggestion: str
    reason: str


class FeedbackState(TypedDict, total=False):
    # 입력
    essay_text: str
    # spelling_agent 출력
    revised_text: str
    spelling_corrections: list[SpellingCorrection]
    spelling_error: str | None  # bareun 실패해도 파이프라인은 계속 진행 (경고용)
    # polish_agent 출력
    polish_suggestions: list[PolishSuggestion]
    overall_comment: str
    error: str | None


def guardrail_input_node(state: FeedbackState) -> dict[str, Any]:
    result = guardrail_service.check_input_safety(state["essay_text"])
    if result.flagged:
        return {"error": f"입력 검증에서 차단됨 ({result.category}): {result.reason}"}
    return {}


def _route_after_guardrail_input(state: FeedbackState) -> str:
    return END if state.get("error") else "spelling_agent"


def spelling_agent_node(state: FeedbackState) -> dict[str, Any]:
    essay_text = state["essay_text"]
    try:
        result = check_spelling(essay_text)
        return {
            "revised_text": result.revised,
            "spelling_corrections": [
                SpellingCorrection(
                    original=c.original, revised=c.revised, category=c.category, comment=c.comment
                )
                for c in result.corrections
            ],
            "spelling_error": None,
        }
    except SpellingServiceError as exc:
        # bareun 실패는 폴백 처리: 원문 그대로 두고 다음 단계(윤문 제안)는 계속 진행
        return {"revised_text": essay_text, "spelling_corrections": [], "spelling_error": str(exc)}


def _build_polish_prompt(state: FeedbackState, rag_context: str) -> str:
    corrections = state.get("spelling_corrections") or []
    corrections_text = (
        "\n".join(f"- '{c['original']}' → '{c['revised']}' ({c['category']}: {c['comment']})" for c in corrections)
        or "(맞춤법 교정 사항 없음)"
    )
    rag_block = f"\n\n[참고 자료] (표현/어문 규범 관련 채점 기준 해설)\n{rag_context}" if rag_context else ""

    return f"""너는 논술 답안의 문장/표현을 다듬는 첨삭 에이전트다. 아래 원문에서, 이미 처리된
맞춤법 교정과는 별개로 어색하거나 논증에 비효과적인 문장·표현을 찾아 "윤문 제안"을 만들어라.

[원문]
{state["essay_text"]}

[bareun.ai 맞춤법 교정 결과] (이미 처리됨 — 아래 내용은 중복 지적하지 마라)
{corrections_text}
{rag_block}

지시사항:
- 맞춤법/띄어쓰기가 아니라 "문장 구조, 어휘 선택, 논증 효과" 관점에서만 제안하라.
- 원문에 실제로 문제가 있는 부분만 지적하라 (억지로 지적을 만들어내지 마라). 문제가 없으면
  polish_suggestions를 빈 배열로 두어도 된다.
- JSON 문자열 값 안에서는 큰따옴표(")를 쓰지 말고, 인용은 작은따옴표(')나 「」를 써라.

반드시 아래 JSON 형식으로만, 다른 설명이나 마크다운 코드블록 없이 답하라.
{{
  "polish_suggestions": [
    {{"original": "<원문 구절>", "suggestion": "<다듬은 표현>", "reason": "<이렇게 고치는 이유>"}}
  ],
  "overall_comment": "<문장/표현 전반에 대한 한두 문장 총평>"
}}"""


def polish_agent_node(state: FeedbackState) -> dict[str, Any]:
    try:
        rag_results = vector_store.query(RAG_QUERY, n_results=RAG_TOP_K)
    except Exception:
        rag_results = []
    rag_context = "\n\n---\n\n".join(
        f"[{r['metadata'].get('source', '')}/{r['metadata'].get('doc_type', '')}] {r['text']}" for r in rag_results
    )

    base_prompt = _build_polish_prompt(state, rag_context)
    last_error = ""

    for attempt in range(1, MAX_ATTEMPTS + 1):
        prompt = base_prompt
        if attempt > 1:
            prompt += f"\n\n[중요] 이전 응답이 올바른 JSON이 아니었다. 오류: {last_error}. JSON 형식만 출력하라."
        try:
            raw = chat_completion([{"role": "user", "content": prompt}], max_tokens=2048)
            data = extract_json(raw)
            suggestions_raw = data.get("polish_suggestions")
            if not isinstance(suggestions_raw, list):
                raise ValueError("polish_suggestions가 리스트가 아닙니다.")
            suggestions = [
                PolishSuggestion(
                    original=str(s.get("original", "")),
                    suggestion=str(s.get("suggestion", "")),
                    reason=str(s.get("reason", "")),
                )
                for s in suggestions_raw
            ]
            return {
                "polish_suggestions": suggestions,
                "overall_comment": str(data.get("overall_comment", "")),
                "error": None,
            }
        except LLMClientError as exc:
            last_error = f"LLM 호출 실패: {exc}"
        except (ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
            last_error = f"응답 파싱 실패: {exc}"

    return {
        "polish_suggestions": [],
        "overall_comment": "",
        "error": f"윤문 제안 생성이 {MAX_ATTEMPTS}회 시도 후에도 실패했습니다: {last_error}",
    }


def build_feedback_graph():
    graph = StateGraph(FeedbackState)
    graph.add_node("guardrail_input", guardrail_input_node)
    graph.add_node("spelling_agent", spelling_agent_node)
    graph.add_node("polish_agent", polish_agent_node)

    graph.add_edge(START, "guardrail_input")
    graph.add_conditional_edges(
        "guardrail_input", _route_after_guardrail_input, {"spelling_agent": "spelling_agent", END: END}
    )
    graph.add_edge("spelling_agent", "polish_agent")
    graph.add_edge("polish_agent", END)

    return graph.compile()


feedback_app = build_feedback_graph()
