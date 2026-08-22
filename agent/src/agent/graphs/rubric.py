"""문제에 맞는 초안 루브릭을 생성하는 그래프."""

from __future__ import annotations

import logging

from langchain_core.messages import HumanMessage
from langfuse import observe
from langgraph.graph import END, START, StateGraph

from agent.integrations.prompts import get_prompt
from agent.model import get_structured_model
from agent.retry import invoke_with_retry
from agent.schemas.rubric import (
    RubricGenerationOutput,
    RubricState,
    RubricSuggestion,
)

MAX_ATTEMPTS = 3

logger = logging.getLogger(__name__)


def _build_prompt(state: RubricState) -> str:
    model_answer = state.request.model_answer or "(제공되지 않음)"
    return get_prompt(
        "rubric-agent",
        content=state.request.content,
        model_answer=model_answer,
    )


@observe(name="rubric:rubric_agent", as_type="span")
def rubric_agent_node(state: RubricState) -> dict[str, object]:
    base_prompt = _build_prompt(state)

    try:
        model = get_structured_model(RubricGenerationOutput)

        def invoke(prompt: str) -> list[RubricSuggestion]:
            result = model.invoke([HumanMessage(content=prompt)])
            return [item.model_copy(update={"max_score": 5}) for item in result.rubrics]

        rubrics = invoke_with_retry(
            invoke,
            base_prompt,
            operation_name="Rubric model",
            max_attempts=MAX_ATTEMPTS,
        )
        return {"rubrics": rubrics, "error": None}
    except Exception as exc:
        logger.exception("Rubric model invocation failed")
        return {
            "rubrics": [],
            "error": f"Rubric Agent가 {MAX_ATTEMPTS}회 시도 후에도 실패했습니다: {exc}",
        }


def build_rubric_graph():
    graph = StateGraph(RubricState)
    graph.add_node("rubric_agent", rubric_agent_node)
    graph.add_edge(START, "rubric_agent")
    graph.add_edge("rubric_agent", END)
    return graph.compile()


rubric_app = build_rubric_graph()
