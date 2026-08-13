from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

from backend.orm.crud import CRUDUser
from backend.orm.models import UserCreate

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

router = APIRouter(
    prefix="/auth",
    tags=["auth"],
)


@router.post("/login")
async def token(
    payload: Annotated[OAuth2PasswordRequestForm, Depends()],
    user_db: Annotated[CRUDUser, Depends()],
):
    found_user = user_db.get_name(payload.username)
    if found_user is None:
        user_db.create(UserCreate(user_name=payload.username))
    return {
        "access_token": payload.username,
        "token_type": "bearer",
    }


@router.get("/my")
async def my(user: Annotated[str, Depends(oauth2_scheme)]):
    return user
