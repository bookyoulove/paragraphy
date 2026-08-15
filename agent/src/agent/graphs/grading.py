"""LangGraph 기반 Supervisor + 검증(가드레일) + RAG + 채점/루브릭 에이전트.

그래프 구조 (6단계 — 논리분석 노드는 이후 단계에서 브랜치로 추가):

    START -> supervisor -> (에러 있으면) END
                         -> guardrail_input -> (유해 콘텐츠면) END
                                             -> rag_agent -> grading_agent
                                                             -> guardrail_output -> END

- supervisor: 입력(루브릭/답안) 검증만 담당. 라우팅 진입점.
- guardrail_input: 학생 답안에 실제 유해 콘텐츠(자해/혐오/불법행위 안내/프롬프트 인젝션)가
  있는지 검사. 논술 주제로 흔한 민감한 사회 이슈(자살/사형제 등을 "논제"로 다루는 것)는
  차단하지 않는다. 걸리면 채점을 진행하지 않고 즉시 종료(hard block).
- rag_agent: 벡터DB(Chroma, `vector_store.py`)에서 채점 근거로 참고할 채점 기준
  해설/실제 채점 사례를 검색해 grading_agent 프롬프트에 추가 컨텍스트로 얹는다.
  Hybrid search/Reranker/HyDE 등 고도화는 다음 단계로 미루고 지금은 단순 의미 검색만.
- grading_agent: llm_client.chat_completion으로 실제 LLM을 호출해 채점 기준별
  1~5점 점수 + 근거 + 개선 방향을 산출. 응답이 JSON으로 파싱되지 않으면 최대
  2회 재시도한다 (컴포넌트 설계서 7절 "AgentGateway 재시도" 규칙 반영).
- guardrail_output: 채점 결과의 "개선 방향"이 학생 답안을 대신 써주는 수준(대필)인지
  검사한다. 걸려도 점수/근거는 지우지 않고 경고만 덧붙인다(soft flag).
"""

from __future__ import annotations

import json
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from app.agents.common import extract_json
from app.services import guardrail_service, vector_store
from app.services.llm_client import LLMClientError, chat_completion

MAX_ATTEMPTS = 3  # 최초 1회 + 재시도 2회
RAG_TOP_K = 4


class RubricItem(TypedDict):
    criteria: str
    description: str
    max_score: int


class CriterionScore(TypedDict):
    criterion: str
    score: int
    max_score: int
    rationale: str
    improvement: str


class GradingState(TypedDict, total=False):
    # 입력
    problem_content: str
    model_answer: str | None
    rubric_items: list[RubricItem]
    user_answer: str
    university: str | None  # RAG 검색 필터용 (경희대/한양대/국립국어원). 없으면 필터 없이 검색
    # RAG
    rag_context: str
    # 출력
    criteria_scores: list[CriterionScore]
    total_score: float
    overall_comment: str
    grammar_errors: list[dict]
    # 제어
    error: str | None
    policy_warning: str | None  # guardrail_output에서 "직접 첨삭" 의심 시 세팅 (soft flag)


def _format_rubric(items: list[RubricItem]) -> str:
    lines = []
    for i, item in enumerate(items, 1):
        lines.append(f"{i}. {item['criteria']} (5점 만점) — {item.get('description') or '(설명 없음)'}")
    return "\n".join(lines)


def _build_prompt(state: GradingState) -> str:
    rubric_text = _format_rubric(state["rubric_items"])
    model_answer_block = state.get("model_answer") or "(제공되지 않음)"
    rag_context = state.get("rag_context") or ""
    rag_block = (
        f"\n\n[참고 자료] (채점 근거로 참고 가능한 채점 기준 해설/실제 채점 사례 — 학생 답안이\n"
        f"아니므로 그대로 인용하지 말고, 채점 판단의 근거로만 활용하라)\n{rag_context}"
        if rag_context
        else ""
    )
    return f"""너는 대입 논술 답안을 채점하는 채점/루브릭 에이전트다. 아래 채점 기준에 따라
학생 답안을 항목별로 1~5점(모든 항목 5점 만점으로 통일됨)으로 채점하고, 각 점수의 근거와
개선 방향을 제시하라.

[문제]
{state["problem_content"]}

[모범답안] (참고용, 없을 수도 있음)
{model_answer_block}

[채점 기준] (아래 항목 각각을 1~5점으로 채점)
{rubric_text}
{rag_block}

[학생 답안]
{state["user_answer"]}

반드시 아래 JSON 형식으로만 답하라. 설명, 마크다운 코드블록(```) 없이 순수 JSON 객체
하나만 출력하라. rationale에는 학생 답안의 구체적인 표현을 인용해 근거를 제시하되,
JSON 문자열 값 안에서는 큰따옴표(")를 절대 쓰지 마라 — 학생 답안의 표현을 인용할 때는
작은따옴표(') 또는 홑낫표(「」)를 사용하라. 큰따옴표는 오직 JSON 구조 자체(키와 값의
경계)에만 쓴다.

{{
  "criteria_scores": [
    {{"criterion": "<채점 기준명, 위 [채점 기준] 목록의 항목명을 토씨 하나 틀리지 않고 그대로>", "score": <1~5 정수>, "max_score": 5, "rationale": "<근거>", "improvement": "<개선 방향>"}}
  ],
  "total_score": <criteria_scores 점수 합계, 숫자>,
  "overall_comment": "<총평 한두 문장>"
}}

[채점 기준] 목록과 같은 순서로, 같은 개수만큼 criteria_scores를 출력하라. criterion 필드는
반드시 [채점 기준]에 적힌 항목명 원문 그대로 써라 — 요약하거나 표현을 바꾸지 마라. 이 이름이
회차마다 달라지면 재채점 시 이전 회차와 항목을 비교할 수 없게 된다."""


def _validate_result(data: dict[str, Any], rubric_items: list[RubricItem]) -> tuple[list[CriterionScore], float, str]:
    criteria_scores_raw = data.get("criteria_scores")
    if not isinstance(criteria_scores_raw, list) or not criteria_scores_raw:
        raise ValueError("criteria_scores가 비어있거나 리스트가 아닙니다.")

    # LLM이 criterion 이름을 토씨 하나까지 원문 그대로 쓰라고 지시해도 가끔 표현을 바꿔서
    # 낼 때가 있다 — 회차 간 비교(초안 비교표, previous_comparison)가 문자열 일치에 기대므로,
    # 개수가 rubric_items와 정확히 같으면 순서를 신뢰해 항목명을 rubric_items의 원문으로
    # 강제 치환한다(위치 기반 정렬). 개수가 다르면(모델이 항목을 합치거나 빠뜨린 경우) 모델이
    # 낸 이름을 그대로 둔다 — 억지로 맞추면 점수와 이름이 어긋날 위험이 더 크다.
    canonical_names = [item["criteria"] for item in rubric_items]
    align_by_position = len(criteria_scores_raw) == len(canonical_names)

    criteria_scores: list[CriterionScore] = []
    for idx, item in enumerate(criteria_scores_raw):
        score = int(item["score"])
        score = max(1, min(5, score))  # 5점 만점 통일 정책을 코드 레벨에서도 강제
        criterion_name = canonical_names[idx] if align_by_position else str(item["criterion"])
        criteria_scores.append(
            CriterionScore(
                criterion=criterion_name,
                score=score,
                max_score=5,
                rationale=str(item.get("rationale", "")),
                improvement=str(item.get("improvement", "")),
            )
        )

    total_score = float(sum(c["score"] for c in criteria_scores))
    overall_comment = str(data.get("overall_comment", ""))
    return criteria_scores, total_score, overall_comment


def supervisor_node(state: GradingState) -> dict[str, Any]:
    if not state.get("rubric_items"):
        return {"error": "채점 기준(rubric_items)이 비어 있습니다."}
    if not state.get("user_answer", "").strip():
        return {"error": "학생 답안(user_answer)이 비어 있습니다."}
    return {}


def _route_after_supervisor(state: GradingState) -> str:
    return END if state.get("error") else "guardrail_input"


def guardrail_input_node(state: GradingState) -> dict[str, Any]:
    result = guardrail_service.check_input_safety(state["user_answer"])
    if result.flagged:
        return {"error": f"입력 검증에서 차단됨 ({result.category}): {result.reason}"}
    return {}


def _route_after_guardrail_input(state: GradingState) -> str:
    return END if state.get("error") else "rag_agent"


def rag_agent_node(state: GradingState) -> dict[str, Any]:
    query_text = state["problem_content"] + "\n" + "\n".join(
        f"{item['criteria']}: {item.get('description', '')}" for item in state["rubric_items"]
    )
    university = state.get("university")

    try:
        results = vector_store.query(query_text, n_results=RAG_TOP_K, where={"university": university} if university else None)
        if not results and university:
            # 대학별 자료가 없는 조합(예: 사용자 직접 입력 문제)이면 필터 없이 재검색
            results = vector_store.query(query_text, n_results=RAG_TOP_K)
    except Exception:
        # 벡터DB 조회 실패는 채점 자체를 막을 이유가 없다 — 컨텍스트 없이 진행
        results = []

    if not results:
        return {"rag_context": ""}

    context = "\n\n---\n\n".join(
        f"[{r['metadata'].get('source', '')}/{r['metadata'].get('doc_type', '')}"
        f"{'/' + r['metadata']['rubric_item'] if r['metadata'].get('rubric_item') else ''}] {r['text']}"
        for r in results
    )
    return {"rag_context": context}


def grading_agent_node(state: GradingState) -> dict[str, Any]:
    base_prompt = _build_prompt(state)
    last_error: str = ""

    for attempt in range(1, MAX_ATTEMPTS + 1):
        prompt = base_prompt
        if attempt > 1:
            prompt += (
                "\n\n[중요] 이전 응답이 올바른 JSON이 아니었다. "
                f"오류: {last_error}. 반드시 위 JSON 형식만, 다른 텍스트 없이 출력하라."
            )
        try:
            # 채점 기준이 많을 경우(예: 국립국어원 9개 준거) 항목별 rationale/improvement까지
            # 포함한 JSON이 길어져 2048 토큰으로는 finish_reason="length"로 잘릴 수 있었다.
            # 실측(9개 기준 기준) 완전한 응답이 약 3200 토큰까지 소요되어 여유를 두고 4096으로 설정.
            raw = chat_completion([{"role": "user", "content": prompt}], max_tokens=4096)
            data = extract_json(raw)
            criteria_scores, total_score, overall_comment = _validate_result(data, state["rubric_items"])
            return {
                "criteria_scores": criteria_scores,
                "total_score": total_score,
                "overall_comment": overall_comment,
                "grammar_errors": [],
                "error": None,
            }
        except LLMClientError as exc:
            last_error = f"LLM 호출 실패: {exc}"
        except (ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
            last_error = f"응답 파싱 실패: {exc}"

    return {"error": f"채점 에이전트가 {MAX_ATTEMPTS}회 시도 후에도 실패했습니다: {last_error}"}


def guardrail_output_node(state: GradingState) -> dict[str, Any]:
    if state.get("error"):
        return {}
    result = guardrail_service.check_direct_writing(state.get("criteria_scores", []))
    if result.flagged:
        return {"policy_warning": result.reason}
    return {"policy_warning": None}


def build_grading_graph():
    graph = StateGraph(GradingState)
    graph.add_node("supervisor", supervisor_node)
    graph.add_node("guardrail_input", guardrail_input_node)
    graph.add_node("rag_agent", rag_agent_node)
    graph.add_node("grading_agent", grading_agent_node)
    graph.add_node("guardrail_output", guardrail_output_node)

    graph.add_edge(START, "supervisor")
    graph.add_conditional_edges("supervisor", _route_after_supervisor, {"guardrail_input": "guardrail_input", END: END})
    graph.add_conditional_edges("guardrail_input", _route_after_guardrail_input, {"rag_agent": "rag_agent", END: END})
    graph.add_edge("rag_agent", "grading_agent")
    graph.add_edge("grading_agent", "guardrail_output")
    graph.add_edge("guardrail_output", END)

    return graph.compile()


grading_app = build_grading_graph()
