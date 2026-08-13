"""POST /api/grading — LangGraph Supervisor + 채점/루브릭 에이전트 호출 엔드포인트.

흐름 (유스케이스 명세서 "채점" / 시퀀스 다이어그램 3번 준용):
  1. user_identifier로 사용자 조회, 없으면 자동 등록 (인증 미도입, 컴포넌트 설계서 7절)
  2. problem_id가 있으면 문제은행에서 문제+채점기준 조회
     없으면 problem_content+rubric_items로 새 문제(사용자 입력) 생성
  3. session_id가 있으면 기존 세션 재사용(소유자·문제 일치 검증), 없으면 새 세션 생성
  4. 답안을 새 UserAnswer 행으로 저장 (재채점 시에도 항상 새 행 — ERD.md 10절 #3)
  5. LangGraph 그래프(grading_app) 실행 → 채점 실패 시에도 답안 원문은 보존하고 커밋
  6. 채점 성공 시 AnalysisResult 저장, 2차 이상이면 직전 회차 대비 점수 비교 포함
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.agents.grading_graph import grading_app
from app.core.db import get_db
from app.models import AnalysisResult, AnalysisSession, Problem, Rubric, User, UserAnswer
from app.schemas.grading import (
    CriterionDeltaOut,
    CriterionScoreOut,
    GradingRequest,
    GradingResponse,
    PreviousComparisonOut,
)

router = APIRouter(prefix="/api", tags=["grading"])


def _get_or_create_user(db: Session, identifier: str) -> User:
    user = db.query(User).filter(User.user_name == identifier).one_or_none()
    if user is None:
        user = User(user_name=identifier)
        db.add(user)
        db.flush()
    return user


def _resolve_problem_and_rubrics(db: Session, req: GradingRequest, user: User) -> tuple[Problem, list[Rubric]]:
    if req.problem_id:
        problem = db.query(Problem).filter(Problem.problem_id == req.problem_id).one_or_none()
        if problem is None:
            raise HTTPException(status_code=404, detail=f"문제를 찾을 수 없습니다: {req.problem_id}")
        rubrics = db.query(Rubric).filter(Rubric.problem_id == problem.problem_id).all()
        if not rubrics:
            raise HTTPException(status_code=400, detail="해당 문제에 등록된 채점 기준이 없습니다.")
        return problem, rubrics

    # 사용자 직접 입력 문제: GradingRequest 검증기에서 problem_content/rubric_items 필수화됨
    assert req.problem_content is not None and req.rubric_items is not None
    title = req.problem_content.strip().splitlines()[0][:60]
    problem = Problem(
        title=title,
        content=req.problem_content,
        model_answer=req.model_answer,
        created_by_user=True,
        user_id=user.user_id,
    )
    db.add(problem)
    db.flush()

    rubrics = [
        Rubric(problem_id=problem.problem_id, criteria=item.criteria, description=item.description, max_score=5)
        for item in req.rubric_items
    ]
    db.add_all(rubrics)
    db.flush()
    return problem, rubrics


def _resolve_session(db: Session, req: GradingRequest, user: User, problem: Problem) -> AnalysisSession:
    if req.session_id:
        session = db.query(AnalysisSession).filter(AnalysisSession.session_id == req.session_id).one_or_none()
        if session is None:
            raise HTTPException(status_code=404, detail=f"세션을 찾을 수 없습니다: {req.session_id}")
        # 인증이 아닌 데이터 정합성 검사 (컴포넌트 설계서 7절 "세션 소유권 검사")
        if session.user_id != user.user_id:
            raise HTTPException(status_code=400, detail="세션 소유자와 요청 사용자(user_identifier)가 일치하지 않습니다.")
        if session.problem_id != problem.problem_id:
            raise HTTPException(status_code=400, detail="세션에 연결된 문제와 요청한 문제가 일치하지 않습니다.")
        return session

    session = AnalysisSession(user_id=user.user_id, problem_id=problem.problem_id)
    db.add(session)
    db.flush()
    return session


def _build_comparison(previous_round: int, previous_scores: list[dict], graph_result: dict) -> PreviousComparisonOut:
    prev_by_criterion = {c["criterion"]: c["score"] for c in previous_scores}
    per_criterion: list[CriterionDeltaOut] = []
    for c in graph_result["criteria_scores"]:
        prev_score = prev_by_criterion.get(c["criterion"])
        if prev_score is None:
            continue
        per_criterion.append(
            CriterionDeltaOut(
                criterion=c["criterion"],
                previous_score=prev_score,
                current_score=c["score"],
                delta=c["score"] - prev_score,
            )
        )
    prev_total = float(sum(prev_by_criterion.values()))
    curr_total = graph_result["total_score"]
    return PreviousComparisonOut(
        previous_round=previous_round,
        previous_total_score=prev_total,
        current_total_score=curr_total,
        total_delta=curr_total - prev_total,
        per_criterion=per_criterion,
    )


@router.post("/grading", response_model=GradingResponse)
def create_grading(req: GradingRequest, db: Session = Depends(get_db)) -> GradingResponse:
    try:
        user = _get_or_create_user(db, req.user_identifier)
        problem, rubrics = _resolve_problem_and_rubrics(db, req, user)
        session = _resolve_session(db, req, user, problem)

        answer = UserAnswer(session_id=session.session_id, user_answer=req.user_answer, status="submitted")
        db.add(answer)
        db.flush()
    except HTTPException:
        db.rollback()
        raise

    answers_in_session = (
        db.query(UserAnswer)
        .filter(UserAnswer.session_id == session.session_id)
        .order_by(UserAnswer.created_at)
        .all()
    )
    round_no = len(answers_in_session)  # 방금 flush한 answer 포함

    rubric_items_state = [
        {"criteria": r.criteria, "description": r.description or "", "max_score": r.max_score} for r in rubrics
    ]

    graph_result = grading_app.invoke(
        {
            "problem_content": problem.content,
            "model_answer": problem.model_answer,
            "rubric_items": rubric_items_state,
            "user_answer": req.user_answer,
            "university": problem.university,
        }
    )

    if graph_result.get("error"):
        # 채점 실패 시에도 답안 원문은 보존 (컴포넌트 설계서 4.2 핵심 처리 규칙)
        db.commit()
        error_msg = graph_result["error"]
        if error_msg.startswith("입력 검증에서 차단됨"):
            raise HTTPException(status_code=400, detail=error_msg)  # 가드레일 차단 (정책 위반)
        raise HTTPException(status_code=502, detail=f"채점 에이전트 실패: {error_msg}")

    previous_comparison = None
    if round_no > 1:
        prev_answer = answers_in_session[-2]
        prev_result = db.query(AnalysisResult).filter(AnalysisResult.answer_id == prev_answer.answer_id).one_or_none()
        if prev_result and prev_result.scores:
            previous_comparison = _build_comparison(round_no - 1, prev_result.scores, graph_result)

    analysis_result = AnalysisResult(
        answer_id=answer.answer_id,
        scores=graph_result["criteria_scores"],
        corrections=None,  # 문법/표현 첨삭(bareun 연동)은 4단계에서 채움
        agent_results={
            "criteria_scores": graph_result["criteria_scores"],
            "total_score": graph_result["total_score"],
            "overall_comment": graph_result["overall_comment"],
            "grammar_errors": graph_result.get("grammar_errors", []),
        },
    )
    db.add(analysis_result)
    db.commit()

    return GradingResponse(
        session_id=session.session_id,
        answer_id=answer.answer_id,
        result_id=analysis_result.result_id,
        problem_id=problem.problem_id,
        round=round_no,
        criteria_scores=[CriterionScoreOut(**c) for c in graph_result["criteria_scores"]],
        total_score=graph_result["total_score"],
        overall_comment=graph_result["overall_comment"],
        previous_comparison=previous_comparison,
        policy_warning=graph_result.get("policy_warning"),
    )
