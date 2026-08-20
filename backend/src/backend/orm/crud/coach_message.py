from backend.orm.crud._base import CRUDBase
from backend.orm.models import CoachMessages
from backend.schema.coach_message import CoachMessageCreate


class CRUDCoachMessage(CRUDBase[CoachMessages, CoachMessageCreate, CoachMessageCreate]): ...
