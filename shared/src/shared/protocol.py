from typing import Protocol

from pydantic import BaseModel

from shared.schema.analysis import AnalysisRequest, AnalysisResult
from shared.schema.recommend import RecommendRequest, RecommendResult
from shared.schema.rubric import RubricGenerationRequest, RubricList
from shared.schema.tutor import TutorChatInput, TutorChatOutput


class AgentProtocol[in_T: BaseModel, out_T: BaseModel](Protocol):
    async def run(self, input: in_T) -> out_T: ...


class RubricAgentProtocol(
    AgentProtocol[RubricGenerationRequest, RubricList], Protocol
): ...


class AnalysisAgentProtocol(
    AgentProtocol[AnalysisRequest, AnalysisResult], Protocol
): ...


class TutorChatAgentProtocol(AgentProtocol[TutorChatInput, TutorChatOutput], Protocol): ...


class RecommendAgentProtocol(AgentProtocol[RecommendRequest, RecommendResult], Protocol): ...
