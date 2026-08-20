from backend.orm.crud._base import CRUDBase
from backend.orm.models import UserAnswers
from backend.schema.user_answer.input import UserAnswerCreate, UserAnswerUpdate


class CRUDUserAnswer(CRUDBase[UserAnswers, UserAnswerCreate, UserAnswerUpdate]): ...
