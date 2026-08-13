from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List

from .database import engine, Base, get_db, SessionLocal
from .models import User, Problem, AnalysisSession, UserAnswer, AnalysisResult, ChatMessage
from .schemas import (
    ProblemOut,
    SessionOut,
    SessionCreate,
    AnswerCreate,
    AnswerOut,
    GradeRequest,
    GradeResultOut,
    ChatMessageIn,
    ChatResponseOut,
)
from .service import grade_answer, chat_agent_reply
from .seed_data import build_seed_problems


def seed_default_data():
    db = SessionLocal()
    try:
        if not db.query(User).filter(User.identifier == "ui_user").first():
            db.add(User(identifier="ui_user"))
        if db.query(Problem).count() == 0:
            db.add_all(Problem(**p) for p in build_seed_problems())
        db.commit()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    seed_default_data()
    yield


app = FastAPI(title="Paragraphy API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:3000", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok", "environment": "local"}


@app.get("/api/problems", response_model=List[ProblemOut])
def list_problems(db: Session = Depends(get_db)):
    return db.query(Problem).order_by(Problem.id.desc()).all()


@app.get("/api/problems/{problem_id}", response_model=ProblemOut)
def get_problem(problem_id: int, db: Session = Depends(get_db)):
    problem = db.query(Problem).filter(Problem.id == problem_id).first()
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")
    return problem


@app.post("/api/sessions", response_model=SessionOut)
def create_session(session_in: SessionCreate, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == session_in.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    session = AnalysisSession(
        user_id=session_in.user_id,
        problem_id=session_in.problem_id,
        problem_source=session_in.problem_source,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@app.get("/api/sessions/user/{user_id}", response_model=List[SessionOut])
def list_sessions(user_id: int, db: Session = Depends(get_db)):
    return db.query(AnalysisSession).filter(AnalysisSession.user_id == user_id).order_by(AnalysisSession.id.desc()).all()


@app.post("/api/answers", response_model=AnswerOut)
def submit_answer(answer: AnswerCreate, db: Session = Depends(get_db)):
    session = db.query(AnalysisSession).filter(AnalysisSession.id == answer.session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    # 세션 단위 upsert: 해당 세션의 draft 답안이 있으면 갱신, 없으면 새로 생성
    user_answer = (
        db.query(UserAnswer)
        .filter(UserAnswer.session_id == answer.session_id, UserAnswer.status == "draft")
        .order_by(UserAnswer.id.desc())
        .first()
    )
    if user_answer:
        user_answer.text = answer.text
        user_answer.status = answer.status
    else:
        user_answer = UserAnswer(session_id=answer.session_id, text=answer.text, status=answer.status)
        db.add(user_answer)
    db.commit()
    db.refresh(user_answer)
    return user_answer


@app.post("/api/grade", response_model=GradeResultOut)
async def grade_session(request: GradeRequest, db: Session = Depends(get_db)):
    session = db.query(AnalysisSession).filter(AnalysisSession.id == request.session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    answer = (
        db.query(UserAnswer)
        .filter(UserAnswer.session_id == session.id)
        .order_by(UserAnswer.created_at.desc(), UserAnswer.id.desc())
        .first()
    )
    if not answer:
        raise HTTPException(status_code=404, detail="Answer not found")

    analysis = await grade_answer(db, session, answer.text)

    result = AnalysisResult(
        session_id=session.id,
        source=request.source,
        scores=analysis["scores"],
        grammar_errors=analysis["grammar_errors"],
        suggestions=analysis["suggestions"],
        commentary=analysis["commentary"],
    )
    db.add(result)
    db.commit()
    db.refresh(result)

    return {
        "session_id": session.id,
        "source": result.source,
        "score": analysis["score"],
        "total_max": analysis["total_max"],
        "scores": result.scores or [],
        "commentary": result.commentary,
        "suggestions": result.suggestions or [],
        "grammar_errors": result.grammar_errors or [],
    }


@app.post("/api/chat", response_model=ChatResponseOut)
async def chat_message(payload: ChatMessageIn, db: Session = Depends(get_db)):
    session = db.query(AnalysisSession).filter(AnalysisSession.id == payload.session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    user_message = ChatMessage(session_id=payload.session_id, role="user", text=payload.text, meta=payload.meta)
    db.add(user_message)
    db.commit()
    db.refresh(user_message)

    history = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session.id)
        .order_by(ChatMessage.id.asc())
        .all()
    )
    reply_text = await chat_agent_reply(db, session, history)

    assistant_message = ChatMessage(session_id=payload.session_id, role="assistant", text=reply_text, meta={"source": "tutor_agent"})
    db.add(assistant_message)
    db.commit()
    db.refresh(assistant_message)

    messages = db.query(ChatMessage).filter(ChatMessage.session_id == session.id).order_by(ChatMessage.id.asc()).all()
    return {"session_id": session.id, "messages": messages}
