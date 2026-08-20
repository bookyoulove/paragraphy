from backend.orm.crud._base import CRUDBase
from backend.orm.models import ChatSessions
from backend.schema.chat_session.input import ChatSessionCreate, ChatSessionUpdate


class CRUDChatSession(CRUDBase[ChatSessions, ChatSessionCreate, ChatSessionUpdate]): ...
