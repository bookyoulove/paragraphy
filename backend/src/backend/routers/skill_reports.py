"""Endpoints for persisted, LLM-generated weekly skill reports."""

from datetime import datetime, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import APIRouter, HTTPException, Query, status
from sqlmodel import select

from backend.depends import (
    AnalysisResultDBDep,
    SkillReportAgentDep,
    UserSkillReportDBDep,
    UserUUIDDep,
)
from backend.orm.models import AnalysisResults, AnalysisSessions, UserAnswers
from backend.schema.skill_report import UserSkillReportCreate, UserSkillReportPublic
from shared.schema.skill_report import GradedAnswerReview, WeeklySkillReportRequest

router = APIRouter(prefix="/skill-reports", tags=["skill-reports"])


def _recent_reviews(
    result_db: AnalysisResultDBDep,
    user_id: UUID,
    period_start: datetime,
    period_end: datetime,
) -> list[AnalysisResults]:
    statement = (
        select(AnalysisResults)
        .join(UserAnswers, AnalysisResults.answer_id == UserAnswers.id)
        .join(AnalysisSessions, UserAnswers.session_id == AnalysisSessions.id)
        .where(AnalysisSessions.user_id == user_id)
        .where(AnalysisResults.created_at >= period_start)
        .where(AnalysisResults.created_at <= period_end)
        .order_by(AnalysisResults.created_at.asc())
    )
    return list(result_db.session.exec(statement).all())


@router.post(
    "/weekly",
    response_model=UserSkillReportPublic,
    status_code=status.HTTP_201_CREATED,
)
async def create_weekly_skill_report(
    user_id: UserUUIDDep,
    result_db: AnalysisResultDBDep,
    report_db: UserSkillReportDBDep,
    agent: SkillReportAgentDep,
    days: int = Query(default=7, ge=1, le=31),
) -> UserSkillReportPublic:
    """Create and persist a report from this user's recent grading evidence."""
    period_end = datetime.now(tz=ZoneInfo("Asia/Seoul"))
    period_start = period_end - timedelta(days=days)
    results = _recent_reviews(result_db, user_id, period_start, period_end)
    if not results:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="최근 기간에 완료된 채점 결과가 없습니다.",
        )

    request = WeeklySkillReportRequest(
        period_start=period_start,
        period_end=period_end,
        reviews=[
            GradedAnswerReview(
                answer_id=result.answer_id,
                graded_at=result.created_at,
                criteria_scores=result.criteria_scores,
                overall_comment=result.overall_comment,
            )
            for result in results
        ],
    )
    report = await agent.run(request)
    created = report_db.create(
        UserSkillReportCreate(
            user_id=user_id,
            period_type="weekly",
            period_start=period_start,
            period_end=period_end,
            review_count=len(results),
            skill_scores=report.skill_scores,
            overall_skill_comment=report.overall_skill_comment,
            next_learning_goal=report.next_learning_goal,
            recommended_actions=report.recommended_actions,
        )
    )
    return UserSkillReportPublic.model_validate(created)
