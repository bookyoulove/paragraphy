from pydantic import BaseModel


class RecommendRequest(BaseModel):
    keyword: str
    force_generate: bool = False


class RecommendedProblem(BaseModel):
    label: str
    category: str
    title: str
    content: str


class GeneratedProblem(BaseModel):
    title: str
    content: str


class RecommendResult(BaseModel):
    matches: list[RecommendedProblem]
    generated: GeneratedProblem | None = None
