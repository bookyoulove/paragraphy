from datetime import datetime
from uuid import UUID

from backend.orm.crud._base import CRUDBase
from backend.orm.models import CoachMessages, CoachMessageStatus
from backend.schema.coach_message import CoachMessageCreate


class CRUDCoachMessage(CRUDBase[CoachMessages, CoachMessageCreate, CoachMessageCreate]):
    def mark_sent(self, message_id: UUID, sent_at: datetime) -> CoachMessages | None:
        return self._set_delivery_status(message_id, CoachMessageStatus.SENT, sent_at)

    def mark_failed(self, message_id: UUID) -> CoachMessages | None:
        return self._set_delivery_status(message_id, CoachMessageStatus.FAILED)

    def _set_delivery_status(
        self,
        message_id: UUID,
        status: CoachMessageStatus,
        sent_at: datetime | None = None,
    ) -> CoachMessages | None:
        message = self.get(message_id)
        if message is None or message.status != CoachMessageStatus.PENDING:
            return None
        message.status = status
        message.sent_at = sent_at
        self.session.add(message)
        self.session.commit()
        self.session.refresh(message)
        return message
