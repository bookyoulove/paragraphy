from sqlmodel import select

from backend.orm.crud._base import CRUDBase
from backend.orm.models import UserCreate, Users, UserUpdate


class CRUDUser(CRUDBase[Users, UserCreate, UserUpdate]):
    def get_name(self, name: str) -> Users | None:
        stmt = select(self.model).where(self.model.user_name == name)
        results = self.session.exec(stmt)
        return results.one_or_none()
