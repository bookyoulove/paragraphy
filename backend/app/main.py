"""FastAPI 앱 뼈대.

라우터는 컴포넌트 설계서 5절 인터페이스 명세 정신을 따르되, 실제 경로는 `/api/...`
네임스페이스로 일관되게 붙인다.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.chat import router as chat_router
from app.api.feedback import router as feedback_router
from app.api.grading import router as grading_router
from app.api.problems import router as problems_router
from app.api.sessions import router as sessions_router
from app.core.db import Base, engine
from app.models import entities  # noqa: F401  (Base.metadata에 테이블 등록 목적)

app = FastAPI(title="Paragraphy API", version="0.1.0")

# 최소 프론트(Vite dev server, 기본 포트 5173)에서 로컬 개발용으로 붙일 수 있게 허용.
# 프로토타입 단계라 오리진을 넓게 허용 — 배포 시 좁혀야 한다.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(problems_router)
app.include_router(sessions_router)
app.include_router(grading_router)
app.include_router(feedback_router)
app.include_router(chat_router)


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
