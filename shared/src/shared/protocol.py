from typing import Protocol

from pydantic import BaseModel

from shared.schema.analysis import AnalysisRequest, AnalysisResult
from shared.schema.rubric import Rubric, RubricGenerationRequest


class AgentProtocol[in_T: BaseModel, out_T: BaseModel](Protocol):
    def run(self, input: in_T) -> out_T: ...


class RubricAgentProtocol(AgentProtocol[RubricGenerationRequest, Rubric], Protocol): ...


class AnalysisAgentProtocol(
    AgentProtocol[AnalysisRequest, AnalysisResult], Protocol
): ...
