from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.orm.session import create_db_and_table
from backend.routers import auth, problems, results, sessions


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_table()
    yield


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(problems.router)
app.include_router(sessions.router)
app.include_router(results.router)


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
