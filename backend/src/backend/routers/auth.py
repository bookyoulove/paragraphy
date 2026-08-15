from typing import Annotated, Literal

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel

from backend.depends import AuthDep, UserDBDep
from backend.schema.user import UserCreate

router = APIRouter(
    prefix="/auth",
    tags=["auth"],
)


class Token(BaseModel):
    access_token: str
    token_type: Literal["bearer"]


@router.post("/login")
async def get_login_token(
    payload: Annotated[OAuth2PasswordRequestForm, Depends()],
    user_db: UserDBDep,
) -> Token:
    found_user = user_db.get_name(payload.username)
    if found_user is None:
        user_db.create(UserCreate(user_name=payload.username))
    return Token(access_token=payload.username, token_type="bearer")


@router.get("/my")
async def my(user: AuthDep) -> str:
    return user
