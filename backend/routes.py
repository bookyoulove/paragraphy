from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Optional

from .database import engine, Base, get_db, SessionLocal
from .models import User, Problem, AnalysisSession, UserAnswer, AnalysisResult, ChatMessage
from .schemas import (
    ProblemOut,
    ProblemCreate,
    SessionOut,
    SessionCreate,
    AnswerCreate,
    AnswerOut,
    GradeRequest,
    GradeResultOut,
    ResultSummaryOut,
    SessionHistoryOut,
    ChatMessageIn,
    ChatResponseOut,
    LoginRequest,
    UserOut,
    RubricGenerateRequest,
    RubricGenerateOut,
)
from .service import grade_answer, chat_agent_reply, generate_rubric, sum_scores
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
    # 이 환경(Elice VS Code 터널)의 프록시 도메인은 매 세션 랜덤 서브도메인이므로 정규식으로 허용
    allow_origin_regex=r"https://.*\.tunnel\.elice\.io",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok", "environment": "local"}


@app.post("/api/login", response_model=UserOut)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    identifier = payload.identifier.strip()
    if not identifier:
        raise HTTPException(status_code=400, detail="identifier is required")
    user = db.query(User).filter(User.identifier == identifier).first()
    if not user:
        user = User(identifier=identifier)
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


@app.get("/api/problems", response_model=List[ProblemOut])
def list_problems(db: Session = Depends(get_db)):
    return db.query(Problem).order_by(Problem.id.desc()).all()


@app.get("/api/problems/{problem_id}", response_model=ProblemOut)
def get_problem(problem_id: int, db: Session = Depends(get_db)):
    problem = db.query(Problem).filter(Problem.id == problem_id).first()
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")
    return problem


@app.post("/api/rubric/generate", response_model=RubricGenerateOut)
async def rubric_generate(payload: RubricGenerateRequest):
    rubric = await generate_rubric(payload.content, payload.title, payload.hint)
    return {"rubric": rubric}


@app.post("/api/problems", response_model=ProblemOut)
def create_problem(payload: ProblemCreate, db: Session = Depends(get_db)):
    problem = Problem(
        title=payload.title.strip(),
        source="사용자입력",
        content=payload.content,
        rubric=payload.rubric,
        model_answer=payload.model_answer,
        created_by=payload.created_by,
        meta={"school": "사용자입력", "exam_type": "직접 입력", "year": "", "category": "사용자입력"},
    )
    db.add(problem)
    db.commit()
    db.refresh(problem)
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


@app.get("/api/sessions/user/{user_id}", response_model=List[SessionHistoryOut])
def list_sessions(user_id: int, db: Session = Depends(get_db)):
    """사용자가 지금까지 작성한 답안 기록(세션) 목록을 최신순으로 반환한다 (답안 기록 화면용)."""
    sessions = (
        db.query(AnalysisSession)
        .filter(AnalysisSession.user_id == user_id)
        .order_by(AnalysisSession.id.desc())
        .all()
    )
    history = []
    for session in sessions:
        has_answer = db.query(UserAnswer).filter(UserAnswer.session_id == session.id).first()
        if not has_answer:
            continue  # 답안을 작성하지 않은 빈 세션은 기록에서 제외
        results = (
            db.query(AnalysisResult)
            .filter(AnalysisResult.session_id == session.id)
            .order_by(AnalysisResult.id.asc())
            .all()
        )
        latest_score = latest_total_max = None
        if results:
            latest_score, latest_total_max = sum_scores(results[-1].scores)
        history.append(
            SessionHistoryOut(
                id=session.id,
                problem_id=session.problem_id,
                problem_title=session.problem.title if session.problem else "직접 입력 문제",
                problem_source=session.problem_source,
                created_at=session.created_at,
                updated_at=session.updated_at,
                attempt_count=len(results),
                latest_score=latest_score,
                latest_total_max=latest_total_max,
            )
        )
    return history


@app.get("/api/sessions/{session_id}", response_model=SessionOut)
def get_session(session_id: int, db: Session = Depends(get_db)):
    session = db.query(AnalysisSession).filter(AnalysisSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@app.get("/api/sessions/{session_id}/answer", response_model=Optional[AnswerOut])
def get_latest_answer(session_id: int, db: Session = Depends(get_db)):
    """세션에 저장된 가장 최근 답안을 반환한다 (기록에서 이어쓰기용)."""
    answer = (
        db.query(UserAnswer)
        .filter(UserAnswer.session_id == session_id)
        .order_by(UserAnswer.created_at.desc(), UserAnswer.id.desc())
        .first()
    )
    return answer


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


@app.get("/api/sessions/{session_id}/results", response_model=List[ResultSummaryOut])
def list_session_results(session_id: int, db: Session = Depends(get_db)):
    """세션 내 채점 시도들을 회차순으로 반환한다 (채점 비교표용)."""
    session = db.query(AnalysisSession).filter(AnalysisSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    results = (
        db.query(AnalysisResult)
        .filter(AnalysisResult.session_id == session_id)
        .order_by(AnalysisResult.id.asc())
        .all()
    )
    summaries = []
    for idx, result in enumerate(results):
        score, total_max = sum_scores(result.scores)
        summaries.append(
            {
                "id": result.id,
                "attempt": idx + 1,
                "created_at": result.created_at,
                "score": score,
                "total_max": total_max,
                "scores": result.scores or [],
                "grammar_error_count": len(result.grammar_errors or []),
                "commentary": result.commentary,
                "suggestions": result.suggestions or [],
                "grammar_errors": result.grammar_errors or [],
            }
        )
    return summaries


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
