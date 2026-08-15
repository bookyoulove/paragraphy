"""LangGraph 기반 Rubric Agent (컴포넌트 설계서 4.5절 C-08).

사용자가 문제를 직접 입력할 때, 국립국어원 채점 기준(3단계에서 색인한 벡터DB)을
참고용 기본 항목으로 삼아 이 문제에 맞는 초기 채점 기준을 제안한다. 최종 채점
항목 리스트는 사용자가 화면에서 수정/추가/삭제해 확정한다 (원 기획서 1절 정책 —
"국립국어원 기준은 참고용 기본 항목으로 제시하되, 최종 채점 항목은 사용자가 확정").

그래프 구조:

    START -> rag_agent -> rubric_agent -> END
"""

from __future__ import annotations

import json
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from app.agents.common import extract_json
from app.services import vector_store
from app.services.llm_client import LLMClientError, chat_completion

MAX_ATTEMPTS = 3
RAG_TOP_K = 6


class RubricSuggestion(TypedDict):
    criteria: str
    description: str
    max_score: int


class RubricAgentState(TypedDict, total=False):
    content: str
    model_answer: str | None
    rag_context: str
    rubrics: list[RubricSuggestion]
    error: str | None


def rag_agent_node(state: RubricAgentState) -> dict[str, Any]:
    query_text = state["content"]
    try:
        results = vector_store.query(query_text, n_results=RAG_TOP_K, where={"source": "국립국어원"})
    except Exception:
        results = []
    context = "\n\n---\n\n".join(
        f"[{r['metadata'].get('doc_type', '')}{'/' + r['metadata']['rubric_item'] if r['metadata'].get('rubric_item') else ''}] {r['text']}"
        for r in results
    )
    return {"rag_context": context}


def _build_prompt(state: RubricAgentState) -> str:
    model_answer_block = state.get("model_answer") or "(제공되지 않음)"
    rag_context = state.get("rag_context") or "(참고자료 없음)"
    return f"""너는 대입 논술 문제의 채점 기준(루브릭)을 설계하는 Rubric Agent다. 아래 문제에
맞는 채점 기준을 국립국어원 논증적 글쓰기 채점 준거(내용/조직/표현 범주, 9개 세부 준거)를
참고하여 제안하라. 이 제안은 초안일 뿐이며, 사용자가 화면에서 직접 수정/추가/삭제한 뒤 확정한다.

[문제]
{state["content"]}

[모범답안] (참고용, 없을 수도 있음)
{model_answer_block}

[참고 자료] (국립국어원 논증적 글쓰기 채점 준거 정의/척도)
{rag_context}

지시사항:
- 국립국어원 9개 준거(문제 상황 제시/다른 입장에 대한 고려/주장/이유·근거의 적절성/
  이유·근거의 충분성/글 전체 조직/문단 내 조직/문장과 어휘/어문 규범과 관습)를 그대로
  베끼지 말고, 이 문제의 성격(제시문 유무, 요약형/논증형, 분량 등)에 맞게 개수와 표현을
  조정하라. 보통 5~9개 항목이 적절하다.
- 각 항목은 "채점 척도는 항목 개수·원배점과 무관하게 모두 5점 만점" 정책에 따라
  max_score는 항상 5로 고정한다.
- description에는 1~5점 중 어떤 수준이 몇 점인지 판단 기준을 짧게 서술하라(상세한
  5단계 척도 전문까지는 필요 없고, 채점자가 참고할 핵심 판단 기준 한두 문장이면 된다).
- JSON 문자열 값 안에서는 큰따옴표(")를 쓰지 마라. 인용은 작은따옴표(')나 「」를 써라.

반드시 아래 JSON 형식으로만, 다른 설명이나 마크다운 코드블록 없이 답하라.
{{
  "rubrics": [
    {{"criteria": "<채점 항목명>", "description": "<채점 판단 기준>", "max_score": 5}}
  ]
}}"""


def rubric_agent_node(state: RubricAgentState) -> dict[str, Any]:
    base_prompt = _build_prompt(state)
    last_error = ""

    for attempt in range(1, MAX_ATTEMPTS + 1):
        prompt = base_prompt
        if attempt > 1:
            prompt += f"\n\n[중요] 이전 응답이 올바른 JSON이 아니었다. 오류: {last_error}. JSON 형식만 출력하라."
        try:
            raw = chat_completion([{"role": "user", "content": prompt}], max_tokens=2048)
            data = extract_json(raw)
            rubrics_raw = data.get("rubrics")
            if not isinstance(rubrics_raw, list) or not rubrics_raw:
                raise ValueError("rubrics가 비어있거나 리스트가 아닙니다.")
            rubrics = [
                RubricSuggestion(
                    criteria=str(item["criteria"]),
                    description=str(item.get("description", "")),
                    max_score=5,  # 정책상 고정
                )
                for item in rubrics_raw
            ]
            return {"rubrics": rubrics, "error": None}
        except LLMClientError as exc:
            last_error = f"LLM 호출 실패: {exc}"
        except (ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
            last_error = f"응답 파싱 실패: {exc}"

    return {"rubrics": [], "error": f"Rubric Agent가 {MAX_ATTEMPTS}회 시도 후에도 실패했습니다: {last_error}"}


def build_rubric_graph():
    graph = StateGraph(RubricAgentState)
    graph.add_node("rag_agent", rag_agent_node)
    graph.add_node("rubric_agent", rubric_agent_node)
    graph.add_edge(START, "rag_agent")
    graph.add_edge("rag_agent", "rubric_agent")
    graph.add_edge("rubric_agent", END)
    return graph.compile()


rubric_app = build_rubric_graph()
