import os
from typing import Literal

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command
from pydantic import BaseModel
from shared.protocol import RubricAgentProtocol
from shared.schema.rubric import RubricGenerationRequest, RubricList

load_dotenv()

BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")
MODEL_NAME = os.getenv("RUBRIC_MODEL_NAME", "gemini-3.1-flash-lite")


model = init_chat_model(MODEL_NAME, model_provider="openai", base_url=BASE_URL)


class RubricState(BaseModel):
    request: RubricGenerationRequest
    result: RubricList | None = None


async def get_rubric(state: RubricState) -> Command[Literal[END]]:
    structured_model = model.with_structured_output(RubricList)
    output = await structured_model.ainvoke(
        [
            SystemMessage(
                "You are a rubric generation agent for essay question. You will be given a question and you need to generate rubrics for it.\n"
                "It has criteria and description - criteria should be a short phrase (<256 chars) that describes the aspect of the answer being evaluated, and description should be a detailed explanation of what is expected for that criteria. If there is no description, you can leave it empty.\n"
                "Keep in mind that description should contain guideline for evaluating the answer from point 1 to 5, where 1 is the worst and 5 is the best.\n"
                "You have to match language of the question and answer.\n"
                "Three rubrics is base case, but you can generate more or less if you think it is appropriate."
            ),
            HumanMessage(f"{state.request.model_dump_json()}"),
        ]
    )
    return Command(goto=END, update={"result": output})


rubric_graph = StateGraph(RubricState)
rubric_graph.add_node("get_rubric", get_rubric)

rubric_graph.add_edge(START, "get_rubric")

rubric_agent = rubric_graph.compile()


class RubricAgent(RubricAgentProtocol):
    async def run(self, input: RubricGenerationRequest) -> RubricList:
        state = RubricState(request=input)
        raw_result = await rubric_agent.ainvoke(state)
        final_state = RubricState.model_validate(raw_result)
        if final_state.result is None:
            raise ValueError("Rubric generation failed, result is None")
        return final_state.result
