from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List

from .database import engine, Base, get_db
from .models import User, Problem, AnalysisSession, UserAnswer, AnalysisResult, ChatMessage
from .schemas import ProblemOut, SessionOut, AnswerCreate, AnswerOut, GradeRequest, GradeResultOut, ChatMessageIn, ChatMessageOut, ChatResponseOut
from .service import grade_answer

app = FastAPI(title="Paragraphy API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:3000", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)


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
def create_session(user_id: int, problem_id: int, problem_source: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    session = AnalysisSession(user_id=user_id, problem_id=problem_id, problem_source=problem_source)
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
    answer = db.query(UserAnswer).filter(UserAnswer.session_id == session.id).order_by(UserAnswer.created_at.desc()).first()
    if not answer:
        raise HTTPException(status_code=404, detail="Answer not found")
    analysis = await grade_answer(session.id, answer.text)
    result = AnalysisResult(
        session_id=session.id,
        source=request.source,
        scores=analysis.get("scores"),
        grammar_errors=analysis.get("grammar_errors"),
        commentary=analysis.get("commentary"),
        tool_responses=analysis.get("tool_responses"),
    )
    db.add(result)
    db.commit()
    db.refresh(result)

    return {
        "session_id": session.id,
        "source": result.source,
        "score": analysis.get("score", 0),
        "scores": result.scores or [],
        "commentary": result.commentary,
        "grammar_errors": result.grammar_errors or [],
        "tool_responses": result.tool_responses or {},
    }


@app.post("/api/chat", response_model=ChatResponseOut)
async def chat_message(payload: ChatMessageIn, db: Session = Depends(get_db)):
    session = db.query(AnalysisSession).filter(AnalysisSession.id == payload.session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    user_message = ChatMessage(session_id=payload.session_id, role="user", text=payload.text, metadata=payload.metadata)
    db.add(user_message)
    db.commit()
    db.refresh(user_message)

    # Simplified chat response from the last grading commentary or template response
    last_result = db.query(AnalysisResult).filter(AnalysisResult.session_id == session.id).order_by(AnalysisResult.id.desc()).first()
    reply_text = ""
    if last_result and last_result.commentary:
        reply_text = f"이 답안의 주요 문제점: {last_result.commentary}"
    else:
        reply_text = "답안을 먼저 채점한 후, 보다 구체적인 첨삭 피드백을 제공하겠습니다."

    assistant_message = ChatMessage(session_id=payload.session_id, role="assistant", text=reply_text, metadata={"source": "auto"})
    db.add(assistant_message)
    db.commit()
    db.refresh(assistant_message)

    messages = db.query(ChatMessage).filter(ChatMessage.session_id == session.id).order_by(ChatMessage.id.asc()).all()
    return {"session_id": session.id, "messages": messages}
