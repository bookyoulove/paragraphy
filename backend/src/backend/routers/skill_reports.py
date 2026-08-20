"""Endpoints for persisted, LLM-generated weekly skill reports."""

from datetime import datetime, timedelta
from email.utils import parseaddr
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, status
from sqlmodel import select

from backend.depends import (
    AnalysisResultDBDep,
    CoachMessageDBDep,
    SkillReportAgentDep,
    UserSkillReportDBDep,
    UserUUIDDep,
)
from backend.orm.models import (
    AnalysisResults,
    AnalysisSessions,
    UserAnswers,
    UserSkillReports,
)
from backend.schema.skill_report import UserSkillReportCreate, UserSkillReportPublic
from backend.schema.coach_message import (
    CoachMessageCreate,
    CoachMessagePublic,
    SendWeeklyReportEmailRequest,
)
from backend.services.email import render_weekly_report_html, send_weekly_report_email
from shared.schema.skill_report import GradedAnswerReview, WeeklySkillReportRequest

router = APIRouter(prefix="/skill-reports", tags=["skill-reports"])


@router.get("/", response_model=list[UserSkillReportPublic])
def get_skill_report_list(
    user_id: UserUUIDDep,
    report_db: UserSkillReportDBDep,
) -> list[UserSkillReportPublic]:
    statement = (
        select(UserSkillReports)
        .where(UserSkillReports.user_id == user_id)
        .order_by(UserSkillReports.period_end.desc())
    )
    reports = report_db.session.exec(statement).all()
    return [UserSkillReportPublic.model_validate(report) for report in reports]


@router.get("/{report_id}", response_model=UserSkillReportPublic)
def get_skill_report(
    report_id: UUID,
    user_id: UserUUIDDep,
    report_db: UserSkillReportDBDep,
) -> UserSkillReportPublic:
    report = report_db.get(report_id)
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="리포트를 찾을 수 없습니다.")
    if report.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="리포트에 접근할 수 없습니다.")
    return UserSkillReportPublic.model_validate(report)


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


@router.post(
    "/{report_id}/email",
    response_model=CoachMessagePublic,
    status_code=status.HTTP_202_ACCEPTED,
)
async def email_weekly_skill_report(
    report_id: UUID,
    request: SendWeeklyReportEmailRequest,
    user_id: UserUUIDDep,
    report_db: UserSkillReportDBDep,
    message_db: CoachMessageDBDep,
    background_tasks: BackgroundTasks,
) -> CoachMessagePublic:
    """Queue an HTML email for an existing weekly report."""
    _, parsed_address = parseaddr(request.recipient_email)
    if "@" not in parsed_address:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="유효한 수신자 이메일을 입력하세요.",
        )
    report = report_db.get(report_id)
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="리포트를 찾을 수 없습니다.")
    if report.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="리포트에 접근할 수 없습니다.")

    message = message_db.create(
        CoachMessageCreate(
            user_id=user_id,
            skill_report_id=report.id,
            recipient_email=parsed_address,
            title="이번 주 논술 리포트가 도착했어요",
            content=render_weekly_report_html(report),
        )
    )
    background_tasks.add_task(send_weekly_report_email, message.id)
    return CoachMessagePublic.model_validate(message)
