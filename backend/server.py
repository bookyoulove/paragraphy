from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from backend.orm.session import create_db_and_table
from backend.routers import auth, problems, session


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_table()
    yield

app = FastAPI(lifespan=lifespan)

app.include_router(auth.router)
app.include_router(problems.router)
app.include_router(session.router)



if __name__ == "__main__":
    uvicorn.run("server:app", reload=True)
