from pydantic import BaseModel


class RecommendRequest(BaseModel):
    keyword: str
    force_generate: bool = False
    # 서버가 인증된 사용자·세션 식별자를 주입하며, 클라이언트 입력으로 신뢰하지 않는다.
    user_identifier: str | None = None
    session_id: str | None = None


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
