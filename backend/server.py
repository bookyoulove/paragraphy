import os
from contextlib import asynccontextmanager
from pathlib import Path

import dotenv
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.misc.db_loader import load_problem
from backend.orm.session import create_db_and_table, get_session
from backend.routers import (
    auth,
    problems,
    results,
    sessions,
    skill_reports,
    webhook_listner,
)

dotenv.load_dotenv()

CORS_ORIGIN = os.getenv(
    "CORS_ORIGIN", "http://localhost:5173,http://127.0.0.1:5173"
).split(",")
CORS_ORIGIN = [origin.strip() for origin in CORS_ORIGIN if origin.strip()]


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_table()
    session = next(get_session())
    load_problem(session)
    yield


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGIN,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(problems.router)
app.include_router(sessions.router)
app.include_router(results.router)
app.include_router(skill_reports.router)
app.include_router(webhook_listner.router)


if __name__ == "__main__":
    project_root = Path(__file__).resolve().parents[1]
    uvicorn.run(
        "server:app",
        reload=True,
        reload_dirs=[
            str(project_root / "backend"),
            str(project_root / "agent"),
            str(project_root / "shared"),
        ],
    )
