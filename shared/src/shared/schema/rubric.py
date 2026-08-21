from pydantic import BaseModel
from sqlmodel import Field, SQLModel


class RubricGenerationRequest(BaseModel):
    content: str
    model_answer: str | None = None
    # Langfuse trace 메타데이터용 (선택, 관측 전용). 루브릭 생성은 세션 생성 전에
    # 일어나므로 session_id는 없다.
    user_identifier: str | None = None


class Rubric(SQLModel):
    criteria: str = Field(max_length=256)
    description: str | None = None

class RubricList(SQLModel):
    rubrics: list[Rubric] = Field(min_length=1)    