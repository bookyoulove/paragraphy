from uuid import UUID

from pydantic import BaseModel, Field

from backend.orm.models import CoachMessageBase


class SendWeeklyReportEmailRequest(BaseModel):
    recipient_email: str = Field(min_length=3, max_length=320)


class CoachMessageCreate(CoachMessageBase):
    user_id: UUID
    skill_report_id: UUID


class CoachMessagePublic(CoachMessageBase):
    id: UUID
