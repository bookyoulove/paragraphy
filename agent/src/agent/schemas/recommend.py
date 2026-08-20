"""문제 추천(하이브리드 RAG) 그래프의 계약 모델."""

from pydantic import BaseModel


class GeneratedProblemOutput(BaseModel):
    title: str
    content: str
