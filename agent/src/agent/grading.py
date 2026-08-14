import os
from typing import Literal

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command
from pydantic import BaseModel
from shared.protocol import AnalysisAgentProtocol
from shared.schema.analysis import AnalysisRequest, AnalysisResult

load_dotenv()

BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")
MODEL_NAME = os.getenv("RUBRIC_MODEL_NAME", "gemini-3.1-flash-lite")


model = init_chat_model(MODEL_NAME, model_provider="openai", base_url=BASE_URL)


class AnalysisState(BaseModel):
    request: AnalysisRequest
    result: AnalysisResult | None = None


async def get_analysis(state: AnalysisState) -> Command[Literal[END]]:
    structured_model = model.with_structured_output(AnalysisResult)
    output = await structured_model.ainvoke(
        [
            SystemMessage(
                "You are an expert in analyzing student answers and providing feedback. You will receive a request containing the student's answer, the model answer, and the rubric. Your task is to analyze the student's answer based on the provided rubric and model answer, and return a structured analysis result.\n"
                "For each rubric, provide criterion (which rubric it is), score (from 1 to 5), rationale (explain why you gave that score), and improvement (how the student can improve). If the student's answer is perfect, you can give a score of 5 and provide positive feedback. If the student's answer is missing or incorrect, provide constructive feedback on how to improve.\n"
                "For grammar check fields, fill it with any value for now as this is testing.\n"
                "You can leave overall comment if you want, but it is optional. If you leave it empty, it will be ignored."
            ),
            HumanMessage(f"{state.request.model_dump_json()}"),
        ]
    )
    return Command(goto=END, update={"result": output})


analysis_graph = StateGraph(AnalysisState)
analysis_graph.add_node("get_rubric", get_analysis)

analysis_graph.add_edge(START, "get_rubric")

rubric_agent = analysis_graph.compile()


class AnalysisAgent(AnalysisAgentProtocol):
    async def run(self, input: AnalysisRequest) -> AnalysisResult:
        state = AnalysisState(request=input)
        raw_result = await rubric_agent.ainvoke(state)
        final_state = AnalysisState.model_validate(raw_result)
        if final_state.result is None:
            raise ValueError("Rubric generation failed, result is None")
        return final_state.result