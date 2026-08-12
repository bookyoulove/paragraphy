from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List

from .database import engine, Base, get_db, SessionLocal
from .models import User, Problem, AnalysisSession, UserAnswer, AnalysisResult, ChatMessage
from .schemas import ProblemOut, SessionOut, SessionCreate, AnswerCreate, AnswerOut, GradeRequest, GradeResultOut, ChatMessageIn, ChatResponseOut
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


@app.on_event("startup")
def seed_default_data():
    db = SessionLocal()
    try:
        if not db.query(User).filter(User.identifier == "ui_user").first():
            db.add(User(identifier="ui_user"))
        if db.query(Problem).count() == 0:
            sample_problems = [
                Problem(
                    title="한양대 상경 논술 2025",
                    source="한양대",
                    content="제시문 (가)와 (나)를 비교하고, 온라인 익명성의 공동체 영향에 대한 견해를 논술하시오.",
                    rubric="내용, 조직, 표현, 논리성, 완성도",
                    model_answer="모범 답안 예시...",
                    meta={"school": "한양대", "exam_type": "상경", "year": "2025", "category": "대학논술"},
                ),
                Problem(
                    title="경희대 인문 논술 2025",
                    source="경희대",
                    content="제시문을 바탕으로 인문학적 통찰과 논리를 담아 학생의 주장을 서술하시오.",
                    rubric="논리성, 근거 제시, 표현력",
                    model_answer="모범 답안 예시...",
                    meta={"school": "경희대", "exam_type": "인문", "year": "2025", "category": "대학논술"},
                ),
                Problem(
                    title="국립국어원 논술 평가 예시",
                    source="국립국어원",
                    content="다음 지문을 읽고, 주제의 의미와 사회적 함의를 서술하시오.",
                    rubric="내용, 표현, 문법, 논리",
                    model_answer="모범 답안 예시...",
                    meta={"school": "국립국어원", "exam_type": "논술", "year": "2025", "category": "국어"},
                ),
            ]
            db.add_all(sample_problems)
        db.commit()
    finally:
        db.close()


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
    session = AnalysisSession(user_id=session_in.user_id, problem_id=session_in.problem_id, problem_source=session_in.problem_source)
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

    assistant_message = ChatMessage(session_id=payload.session_id, role="assistant", text=reply_text, meta={"source": "auto"})
    db.add(assistant_message)
    db.commit()
    db.refresh(assistant_message)

    messages = db.query(ChatMessage).filter(ChatMessage.session_id == session.id).order_by(ChatMessage.id.asc()).all()
    return {"session_id": session.id, "messages": messages}
