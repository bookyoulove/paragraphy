"""문제 추천(하이브리드 RAG) 그래프의 계약 모델."""

from pydantic import BaseModel
from shared.schema.recommend import RecommendRequest, RecommendResult


class GeneratedProblemOutput(BaseModel):
    title: str
    content: str


class RecommendState(BaseModel):
    request: RecommendRequest
    result: RecommendResult | None = None
    error: str | None = None
