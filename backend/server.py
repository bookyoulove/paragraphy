from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from backend.orm.session import create_db_and_table
from backend.routers import auth


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_table()
    yield

app = FastAPI(lifespan=lifespan)

app.include_router(auth.router)



if __name__ == "__main__":
    uvicorn.run("server:app", reload=True)
