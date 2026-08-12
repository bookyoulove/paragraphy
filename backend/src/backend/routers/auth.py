from datetime import datetime
from typing import Annotated
from uuid import uuid4
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Form
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel

FAKE_DB = [
    {
        "user_id": uuid4(),
        "user_name": "testUser",
        "timestamp": datetime.now(tz=ZoneInfo("Asia/Seoul")),
    }
]


class User(BaseModel):
    id: str


class LoginRequest(BaseModel):
    id: str


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

router = APIRouter(
    prefix="/auth",
    tags=["auth"],
    # dependencies=[auth db dependency]
)


@router.post("/login")
async def token(payload: Annotated[LoginRequest, Form()]):
    for next_db in FAKE_DB:
        if next_db["user_name"] == payload.id:
            break
    else:
        FAKE_DB.append(
            {
                "user_id": uuid4(),
                "user_name": payload.id,
                "timestamp": datetime.now(tz=ZoneInfo("Asia/Seoul")),
            }
        )
    return {
        "access_token": payload.id,
        "token_type": "bearer",
    }
    # TODO
