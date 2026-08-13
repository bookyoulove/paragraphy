"""POST /api/feedback — 문법/표현 첨삭 에이전트(bareun.ai 맞춤법 + LLM 윤문 제안) 엔드포인트.

- essay_text만 주면 저장 없이 첨삭 결과만 반환 (원 기획서 5절 원안: 입력=에세이 텍스트).
- answer_id를 함께 주면 해당 답안의 AnalysisResult.corrections에 결과를 병합 저장한다
  (해당 답안에 채점 결과가 아직 없으면 corrections만 채운 AnalysisResult를 새로 만든다).
- bareun/LLM 중 하나가 실패해도 전체 요청을 실패시키지 않고, 실패 사유를
  spelling_error/polish_error 필드에 남기고 나머지는 정상 반환한다 (에이전트 폴백 처리).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.agents.feedback_graph import feedback_app
from app.core.db import get_db
from app.models import AnalysisResult, UserAnswer
from app.schemas.feedback import (
    FeedbackRequest,
    FeedbackResponse,
    PolishSuggestionOut,
    SpellingCorrectionOut,
)

router = APIRouter(prefix="/api", tags=["feedback"])


@router.post("/feedback", response_model=FeedbackResponse)
def create_feedback(req: FeedbackRequest, db: Session = Depends(get_db)) -> FeedbackResponse:
    result = feedback_app.invoke({"essay_text": req.essay_text})

    guardrail_error = result.get("error")
    if guardrail_error and guardrail_error.startswith("입력 검증에서 차단됨"):
        raise HTTPException(status_code=400, detail=guardrail_error)

    corrections_payload = {
        "revised_text": result.get("revised_text", req.essay_text),
        "spelling_corrections": result.get("spelling_corrections", []),
        "polish_suggestions": result.get("polish_suggestions", []),
        "overall_comment": result.get("overall_comment", ""),
    }

    saved_result_id = None
    if req.answer_id:
        answer = db.query(UserAnswer).filter(UserAnswer.answer_id == req.answer_id).one_or_none()
        if answer is None:
            raise HTTPException(status_code=404, detail=f"답안을 찾을 수 없습니다: {req.answer_id}")

        analysis_result = (
            db.query(AnalysisResult).filter(AnalysisResult.answer_id == answer.answer_id).one_or_none()
        )
        if analysis_result is None:
            # 채점 없이 첨삭만 먼저 요청된 경우 — corrections만 채운 결과 행을 새로 만든다
            analysis_result = AnalysisResult(answer_id=answer.answer_id, scores=None, corrections=corrections_payload)
            db.add(analysis_result)
        else:
            analysis_result.corrections = corrections_payload
        db.flush()
        saved_result_id = analysis_result.result_id
        db.commit()

    return FeedbackResponse(
        origin=req.essay_text,
        revised_text=result.get("revised_text", req.essay_text),
        spelling_corrections=[SpellingCorrectionOut(**c) for c in result.get("spelling_corrections", [])],
        spelling_error=result.get("spelling_error"),
        polish_suggestions=[PolishSuggestionOut(**p) for p in result.get("polish_suggestions", [])],
        polish_error=result.get("error"),
        overall_comment=result.get("overall_comment", ""),
        saved_to_result_id=saved_result_id,
    )
