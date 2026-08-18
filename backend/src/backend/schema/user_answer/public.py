from uuid import UUID

from backend.orm.models import UserAnswerBase


class UserAnswerPublic(UserAnswerBase):
    id: UUID
