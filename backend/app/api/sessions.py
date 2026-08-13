"""GET /api/sessions, GET /api/sessions/{id} — 과거 세션 목록/상세 조회.

유스케이스 명세서 "과거 세션 불러오기": user_identifier로 그 사용자의 과거 첨삭
목록(문제 제목, 생성 일시 등)을 조회하고, 세션 하나를 골라 회차별 답안·채점
결과(초안 비교표 재료)를 본다.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models import AnalysisResult, AnalysisSession, Problem, User, UserAnswer
from app.schemas.session import RoundOut, SessionDetailOut, SessionListItemOut

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


@router.get("", response_model=list[SessionListItemOut])
def list_sessions(user_identifier: str, db: Session = Depends(get_db)) -> list[SessionListItemOut]:
    user = db.query(User).filter(User.user_name == user_identifier).one_or_none()
    if user is None:
        return []  # 아직 한 번도 채점을 요청한 적 없는 식별자 — 빈 목록

    sessions = (
        db.query(AnalysisSession)
        .filter(AnalysisSession.user_id == user.user_id)
        .order_by(AnalysisSession.created_at.desc())
        .all()
    )

    items: list[SessionListItemOut] = []
    for s in sessions:
        problem = db.query(Problem).filter(Problem.problem_id == s.problem_id).one()
        answers = (
            db.query(UserAnswer)
            .filter(UserAnswer.session_id == s.session_id)
            .order_by(UserAnswer.created_at)
            .all()
        )
        latest_total_score = None
        latest_round_at = None
        if answers:
            latest_answer = answers[-1]
            latest_round_at = latest_answer.created_at
            latest_result = (
                db.query(AnalysisResult).filter(AnalysisResult.answer_id == latest_answer.answer_id).one_or_none()
            )
            if latest_result and latest_result.agent_results:
                latest_total_score = latest_result.agent_results.get("total_score")

        items.append(
            SessionListItemOut(
                session_id=s.session_id,
                problem_id=problem.problem_id,
                problem_title=problem.title,
                university=problem.university,
                year=problem.year,
                created_at=s.created_at,
                round_count=len(answers),
                latest_total_score=latest_total_score,
                latest_round_at=latest_round_at,
            )
        )
    return items


@router.get("/{session_id}", response_model=SessionDetailOut)
def get_session(session_id: str, db: Session = Depends(get_db)) -> SessionDetailOut:
    session = db.query(AnalysisSession).filter(AnalysisSession.session_id == session_id).one_or_none()
    if session is None:
        raise HTTPException(status_code=404, detail=f"세션을 찾을 수 없습니다: {session_id}")
    problem = db.query(Problem).filter(Problem.problem_id == session.problem_id).one()

    answers = (
        db.query(UserAnswer)
        .filter(UserAnswer.session_id == session_id)
        .order_by(UserAnswer.created_at)
        .all()
    )

    rounds: list[RoundOut] = []
    for i, answer in enumerate(answers, start=1):
        result = db.query(AnalysisResult).filter(AnalysisResult.answer_id == answer.answer_id).one_or_none()
        agent_results = (result.agent_results if result else None) or {}
        rounds.append(
            RoundOut(
                round=i,
                answer_id=answer.answer_id,
                user_answer=answer.user_answer,
                submitted_at=answer.created_at,
                result_id=result.result_id if result else None,
                criteria_scores=result.scores if result else None,
                total_score=agent_results.get("total_score"),
                overall_comment=agent_results.get("overall_comment"),
            )
        )

    return SessionDetailOut(
        session_id=session.session_id,
        problem_id=problem.problem_id,
        problem_title=problem.title,
        problem_content=problem.content,
        university=problem.university,
        year=problem.year,
        rounds=rounds,
    )
