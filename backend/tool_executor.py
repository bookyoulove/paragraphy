"""Tutor Chat 에이전트가 호출하는 도구 정의 + 실행기.

설계 원칙: 에이전트는 DB에 직접 접근하지 않고, 세션에 스코프된 ToolExecutor를
통해서만 조회한다. 도구 파라미터에는 session_id를 받지 않는다 — 항상 서버가
바인딩한 현재 세션만 조회하도록 하여 다른 세션의 데이터가 노출되지 않게 한다.
"""

from sqlalchemy.orm import Session
from .models import AnalysisSession, AnalysisResult, Problem

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_feedback",
            "description": "현재 세션에서 가장 최근에 산출된 채점 결과(총점, 준거별 점수, 총평, 수정 방향, 어문/표현 오류 목록)를 가져온다.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_problem_index",
            "description": "현재 세션이 속한 문제의 제목·출처·원문(제시문)·채점기준 정보를 가져온다.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_model_answer",
            "description": "현재 문제의 모범답안(등록되어 있는 경우)을 가져온다.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
]


class ToolExecutor:
    def __init__(self, db: Session, session: AnalysisSession):
        self.db = db
        self.session = session

    def call(self, name: str, arguments: dict) -> dict:
        handler = getattr(self, f"_tool_{name}", None)
        if handler is None:
            return {"error": f"알 수 없는 도구입니다: {name}"}
        return handler()

    def _tool_get_feedback(self) -> dict:
        result = (
            self.db.query(AnalysisResult)
            .filter(AnalysisResult.session_id == self.session.id)
            .order_by(AnalysisResult.id.desc())
            .first()
        )
        if not result:
            return {"available": False, "message": "아직 채점 결과가 없습니다. 먼저 채점을 요청해야 합니다."}
        return {
            "available": True,
            "scores": result.scores,
            "commentary": result.commentary,
            "grammar_errors": result.grammar_errors,
            "suggestions": result.suggestions,
        }

    def _tool_get_problem_index(self) -> dict:
        problem = self.db.query(Problem).filter(Problem.id == self.session.problem_id).first()
        if not problem:
            return {"available": False}
        return {
            "available": True,
            "title": problem.title,
            "source": problem.source,
            "content": problem.content,
            "rubric": problem.rubric,
        }

    def _tool_get_model_answer(self) -> dict:
        problem = self.db.query(Problem).filter(Problem.id == self.session.problem_id).first()
        if not problem or not problem.model_answer:
            return {"available": False, "message": "등록된 모범답안이 없습니다."}
        return {"available": True, "model_answer": problem.model_answer}
