"""GET /api/problems, GET /api/problems/{id} — 문제은행 조회 (프론트 문제 선택용).
POST /api/problems/rubric — Rubric Agent: 사용자 직접 입력 문제의 초기 채점 기준 제안.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.agents.rubric_graph import rubric_app
from app.core.db import get_db
from app.models import Problem, Rubric
from app.schemas.problem import (
    ProblemDetailOut,
    ProblemListItemOut,
    RubricOut,
    RubricSuggestionOut,
    RubricSuggestRequest,
    RubricSuggestResponse,
)

router = APIRouter(prefix="/api/problems", tags=["problems"])


@router.get("", response_model=list[ProblemListItemOut])
def list_problems(university: str | None = None, db: Session = Depends(get_db)) -> list[ProblemListItemOut]:
    query = db.query(Problem).filter(Problem.created_by_user.is_(False))
    if university:
        query = query.filter(Problem.university == university)
    problems = query.order_by(Problem.university, Problem.year, Problem.title).all()
    return [
        ProblemListItemOut(
            problem_id=p.problem_id,
            title=p.title,
            university=p.university,
            year=p.year,
            created_by_user=p.created_by_user,
        )
        for p in problems
    ]


@router.get("/{problem_id}", response_model=ProblemDetailOut)
def get_problem(problem_id: str, db: Session = Depends(get_db)) -> ProblemDetailOut:
    problem = db.query(Problem).filter(Problem.problem_id == problem_id).one_or_none()
    if problem is None:
        raise HTTPException(status_code=404, detail=f"문제를 찾을 수 없습니다: {problem_id}")
    rubrics = db.query(Rubric).filter(Rubric.problem_id == problem_id).all()
    return ProblemDetailOut(
        problem_id=problem.problem_id,
        title=problem.title,
        content=problem.content,
        model_answer=problem.model_answer,
        university=problem.university,
        year=problem.year,
        created_by_user=problem.created_by_user,
        rubrics=[
            RubricOut(rubric_id=r.rubric_id, criteria=r.criteria, description=r.description, max_score=r.max_score)
            for r in rubrics
        ],
    )


@router.post("/rubric", response_model=RubricSuggestResponse)
def suggest_rubric(req: RubricSuggestRequest) -> RubricSuggestResponse:
    """Rubric Agent 호출. 결과는 제안일 뿐이며 저장하지 않는다 — 사용자가 수정/확정한 뒤
    /api/grading 요청의 rubric_items로 그대로 넘기면 된다."""
    result = rubric_app.invoke({"content": req.content, "model_answer": req.model_answer})
    if result.get("error"):
        return RubricSuggestResponse(rubrics=[], error=result["error"])
    return RubricSuggestResponse(rubrics=[RubricSuggestionOut(**r) for r in result["rubrics"]])
