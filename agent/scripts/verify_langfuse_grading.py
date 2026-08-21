"""실제 채점 요청 1건을 facade.AnalysisAgent를 통해 실행하고, Langfuse에 trace가
정상적으로 찍히는지(순서대로 span이 나오는지, user_id/session_id가 붙는지) 검증한다.

FastAPI/DB/인증 계층을 거치지 않고 agent 패키지의 공개 진입점(facade.py)을 직접
호출한다 — Langfuse 계측이 실제로 붙어 있는 지점이 바로 이 경로이므로, 백엔드
라우터가 이 값을 채워 넘겨주는 것과 동일한 조건으로 검증하기에 충분하다.

실행:
    uv run --package agent python agent/scripts/verify_langfuse_grading.py
"""

from __future__ import annotations

import asyncio
import sys
from datetime import datetime
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from langfuse.api.commons.types.observations_view import ObservationsView
from shared.schema.analysis import AnalysisRequest
from shared.schema.problem import ProblemWithRubrics
from shared.schema.rubric import Rubric

from agent.facade import AnalysisAgent
from agent.integrations.langfuse_client import get_langfuse_client


def _observation_start_time(observation: ObservationsView) -> datetime:
    return observation.start_time


async def main() -> None:
    client = get_langfuse_client()
    if client is None:
        raise SystemExit("Langfuse가 설정되어 있지 않습니다 (.env 확인).")

    user_identifier = f"verify-user-{uuid4().hex[:8]}"
    session_id = str(uuid4())

    request = AnalysisRequest(
        user_answer="로봇세는 필요하다. 왜냐하면 필요하기 때문이다.",
        problem=ProblemWithRubrics(
            title="로봇세 도입 찬반",
            content="로봇세를 도입해야 하는가? 자신의 의견을 논리적으로 제시하는 글을 쓰시오.",
            model_answer=None,
            rubrics=[
                Rubric(
                    criteria="주장",
                    description="논제에 대한 자신의 주장을 명확하게 제시하는가.",
                ),
                Rubric(
                    criteria="이유/근거의 적절성",
                    description="제시한 이유·근거가 주장과 논리적으로 타당하게 연결되는가.",
                ),
                Rubric(
                    criteria="어문 규범과 관습",
                    description="맞춤법·띄어쓰기 등 어문 규범을 지키는가.",
                ),
            ],
        ),
        user_identifier=user_identifier,
        session_id=session_id,
    )

    agent = AnalysisAgent()

    # facade.AnalysisAgent.run은 @observe로 감싸여 있어, 실행 도중에는
    # get_current_trace_id()로 현재 trace id를 얻을 수 있다. run() 자체는
    # trace id를 반환하지 않으므로, 실행 직후 클라이언트가 기억하는 마지막
    # trace id 대신 API로 최근 trace를 조회해 확인한다.
    result = await agent.run(request)
    print("=== 채점 결과 ===")
    print("overall_comment:", result.overall_comment)
    print("criteria_scores:", [(c.criterion, c.score) for c in result.criteria_scores])

    client.flush()
    await asyncio.sleep(6)

    traces = client.api.trace.list(name="grading-request", limit=5)
    matched = next((t for t in traces.data if t.session_id == session_id), None)
    if matched is None:
        raise SystemExit(
            "방금 실행한 trace를 찾지 못했습니다 (인제스트 지연일 수 있음)."
        )

    print("\n=== Langfuse trace ===")
    print("trace_id:", matched.id)
    print("name:", matched.name)
    print("user_id:", matched.user_id)
    print("session_id:", matched.session_id)
    print("metadata:", matched.metadata)
    print("dashboard url:", client.get_trace_url(trace_id=matched.id))

    full_trace = client.api.trace.get(matched.id)
    print("\n=== span 순서 (name, type, parent) ===")
    for obs in sorted(full_trace.observations, key=_observation_start_time):
        print(f"- {obs.name} [{obs.type}] parent={obs.parent_observation_id}")


asyncio.run(main())
