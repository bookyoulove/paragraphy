"""Endpoints for persisted, LLM-generated weekly skill reports."""

from datetime import datetime, timedelta
from email.utils import parseaddr
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, status
from shared.schema.recommend import RecommendRequest
from shared.schema.rubric import RubricGenerationRequest
from shared.schema.skill_report import GradedAnswerReview, WeeklySkillReportRequest

from backend.depends import (
    AnalysisResultDBDep,
    CoachMessageDBDep,
    ProblemDBDep,
    RecommendAgentDep,
    RubricAgentDep,
    RubricDBDep,
    SkillReportAgentDep,
    UserSkillReportDBDep,
    UserUUIDDep,
)
from backend.schema.coach_message import (
    CoachMessageCreate,
    CoachMessagePublic,
    SendWeeklyReportEmailRequest,
)
from backend.schema.problem.input import ProblemCreate
from backend.schema.problem.response import ProblemPublicWithRubrics
from backend.schema.rubric.input import RubricCreate
from backend.schema.skill_report import UserSkillReportCreate, UserSkillReportPublic
from backend.services.email import render_weekly_report_html, send_weekly_report_email

router = APIRouter(prefix="/skill-reports", tags=["skill-reports"])

SKILL_LABELS = {
    "claim": "주장",
    "evidence_relevance": "이유·근거의 적절성",
    "evidence_sufficiency": "이유·근거의 충분성",
    "counterargument": "다른 입장에 대한 고려",
    "passage_summary": "지문 요약",
}


@router.get("/", response_model=list[UserSkillReportPublic])
def get_skill_report_list(
    user_id: UserUUIDDep,
    report_db: UserSkillReportDBDep,
) -> list[UserSkillReportPublic]:
    reports = report_db.get_by_user(user_id)
    return [UserSkillReportPublic.model_validate(report) for report in reports]


@router.get("/{report_id}", response_model=UserSkillReportPublic)
def get_skill_report(
    report_id: UUID,
    user_id: UserUUIDDep,
    report_db: UserSkillReportDBDep,
) -> UserSkillReportPublic:
    report = report_db.get(report_id)
    if report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="리포트를 찾을 수 없습니다."
        )
    if report.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="리포트에 접근할 수 없습니다."
        )
    return UserSkillReportPublic.model_validate(report)


@router.post("/{report_id}/generated-problem", response_model=ProblemPublicWithRubrics)
async def generate_problem_from_report(
    report_id: UUID,
    user_id: UserUUIDDep,
    report_db: UserSkillReportDBDep,
    problem_db: ProblemDBDep,
    rubric_db: RubricDBDep,
    recommend_agent: RecommendAgentDep,
    rubric_agent: RubricAgentDep,
) -> ProblemPublicWithRubrics:
    report = report_db.get(report_id)
    if report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="리포트를 찾을 수 없습니다."
        )
    if report.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="리포트에 접근할 수 없습니다."
        )

    if not report.skill_scores:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="취약 역량 정보가 없는 리포트입니다.",
        )

    weakest = min(report.skill_scores, key=lambda score: score.score)
    weakest_label = SKILL_LABELS.get(weakest.key, weakest.key)
    generated = await recommend_agent.run(
        RecommendRequest(
            keyword=(
                f"{weakest_label} 역량을 보완하는 논증적 글쓰기. "
                f"학습 개선 방향: {weakest.improvement}"
            ),
            force_generate=True,
            user_identifier=str(user_id),
            session_id=str(report.id),
        )
    )
    if generated.generated is None:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="맞춤 문제 생성에 실패했습니다.",
        )

    problem = problem_db.create(
        ProblemCreate(
            user_id=user_id,
            source_report_id=report.id,
            created_by_user=True,
            title=generated.generated.title,
            content=generated.generated.content,
            model_answer=None,
        )
    )
    rubrics = await rubric_agent.run(
        RubricGenerationRequest(
            content=problem.content,
            model_answer=None,
            user_identifier=str(user_id),
        )
    )
    for rubric in rubrics.rubrics:
        rubric_db.create(
            RubricCreate(
                problem_id=problem.id,
                criteria=rubric.criteria,
                description=rubric.description,
            )
        )
    # 루브릭 관계를 다시 조회해 응답에 함께 담는다.
    saved_problem = problem_db.get(problem.id)
    return ProblemPublicWithRubrics.model_validate(saved_problem)


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
    results = result_db.get_by_user_and_period(user_id, period_start, period_end)
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
        user_identifier=str(user_id),
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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="리포트를 찾을 수 없습니다."
        )
    if report.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="리포트에 접근할 수 없습니다."
        )

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
