from backend.orm.crud._base import CRUDBase
from backend.orm.models import ChatMessages
from backend.schema.chat_message.input import ChatMessageCreate, ChatMessageUpdate


class CRUDChatMessage(CRUDBase[ChatMessages, ChatMessageCreate, ChatMessageUpdate]): ...
