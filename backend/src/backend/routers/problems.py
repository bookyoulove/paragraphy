from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from shared.schema.recommend import RecommendRequest, RecommendResult
from shared.schema.rubric import RubricGenerationRequest

from backend.depends import (
    AnalysisResultDBDep,
    AnalysisSessionDBDep,
    ChatMessageDBDep,
    ChatSessionDBDep,
    ProblemDBDep,
    RecommendAgentDep,
    RubricAgentDep,
    RubricDBDep,
    UserAnswerDBDep,
    UserUUIDDep,
)
from backend.schema.problem.input import (
    Criteria,
    CustomProblemCreate,
    ProblemCreate,
)
from backend.schema.problem.public import ProblemPublic
from backend.schema.problem.response import ProblemPublicWithRubrics
from backend.schema.rubric.input import RubricCreate, RubricDraft
from backend.services.deletion import delete_session_cascade

router = APIRouter(
    prefix="/problems",
    tags=["problems"],
)


@router.get("/", response_model=list[ProblemPublic])
def get_problem_list(
    criteria: Annotated[Criteria, Query()],
    user_id: UserUUIDDep,
    problem_db: ProblemDBDep,
):
    return problem_db.get_criteria(user_id, criteria)


@router.post("/rubric-gen", response_model=list[RubricDraft])
async def generate_rubric(
    request: RubricGenerationRequest,
    user_id: UserUUIDDep,
    agent: RubricAgentDep,
):
    # user_identifier는 요청 바디가 아니라 인증된 user_id로 서버가 직접 채운다
    # (클라이언트가 다른 사용자 식별자를 흉내 낼 수 없게 함 — 관측용 필드라도).
    scoped_request = request.model_copy(update={"user_identifier": str(user_id)})
    rubric_list = await agent.run(scoped_request)
    return rubric_list.rubrics


@router.post("/recommend", response_model=RecommendResult)
async def recommend_problems(
    request: RecommendRequest,
    user_id: UserUUIDDep,
    agent: RecommendAgentDep,
):
    scoped_request = request.model_copy(
        update={"user_identifier": str(user_id), "session_id": None}
    )
    return await agent.run(scoped_request)


@router.post("/custom", response_model=ProblemPublicWithRubrics)
def create_custom_problem(
    request: CustomProblemCreate,
    user_id: UserUUIDDep,
    problem_db: ProblemDBDep,
    rubric_db: RubricDBDep,
):
    problem = problem_db.create(
        ProblemCreate(
            user_id=user_id,
            created_by_user=True,
            title=request.title,
            content=request.content,
            model_answer=request.model_answer,
        )
    )
    problem_id = problem.id
    for rubric in request.rubrics:
        rubric_db.create(
            RubricCreate(
                problem_id=problem_id,
                criteria=rubric.criteria,
                description=rubric.description,
            )
        )
    return problem


@router.delete("/{problem_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_problem(
    problem_id: UUID,
    user_id: UserUUIDDep,
    problem_db: ProblemDBDep,
    rubric_db: RubricDBDep,
    analysis_session_db: AnalysisSessionDBDep,
    user_answer_db: UserAnswerDBDep,
    analysis_result_db: AnalysisResultDBDep,
    chat_session_db: ChatSessionDBDep,
    chat_message_db: ChatMessageDBDep,
):
    problem = problem_db.get(problem_id)
    if not problem or not problem.created_by_user or problem.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Problem not found.",
        )

    for session in list(problem.analysis_sessions):
        delete_session_cascade(
            session,
            analysis_result_db,
            chat_session_db,
            chat_message_db,
            user_answer_db,
        )
        analysis_session_db.delete(session.id)
    for rubric in list(problem.rubrics):
        rubric_db.delete(rubric.id)
    problem_db.delete(problem_id)
