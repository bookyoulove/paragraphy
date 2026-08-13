from pydantic import BaseModel

from backend.orm.models import UserBase


class UserCreate(UserBase): ...


class UserUpdate(BaseModel):
    user_name: str | None = None
