from datetime import datetime
from uuid import UUID

from backend.orm.models import UserAnswerBase


class UserAnswerPublic(UserAnswerBase):
    id: UUID
    created_at: datetime
