from typing import Annotated

from fastapi import APIRouter, Query
from shared.schema.rubric import RubricGenerationRequest

from backend.depends import ProblemDBDep, RubricAgentDep, RubricDBDep, UserUUIDDep
from backend.schema.problem import (
    Criteria,
    CustomProblemCreate,
    ProblemCreate,
    ProblemPublic,
    ProblemPublicWithRubrics,
)
from backend.schema.rubric import RubricCreate, RubricDraft

router = APIRouter(
    prefix="/problems",
    tags=["problems"],
)


@router.get("/", response_model=list[ProblemPublic])
def problem_list(
    criteria: Annotated[Criteria, Query()],
    user_id: UserUUIDDep,
    problem_db: ProblemDBDep,
):
    return problem_db.get_criteria(user_id, criteria)


@router.post("/rubric-gen", response_model=RubricDraft)
def rubric_gen(
    request: RubricGenerationRequest,
    user_id: UserUUIDDep,
    agent: RubricAgentDep,
):
    return agent.run(request)


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
