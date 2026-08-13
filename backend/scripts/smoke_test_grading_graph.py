"""grading_graph 단독 스모크 테스트 (DB/HTTP 없이, 실제 LLM 호출만 검증)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.agents.grading_graph import grading_app  # noqa: E402

state = {
    "problem_content": "다음 제시문을 읽고, 로봇세 도입에 대한 자신의 의견을 논리적으로 제시하는 글을 쓰시오.",
    "model_answer": None,
    "rubric_items": [
        {"criteria": "주장", "description": "논제에 대한 자신의 주장을 명확하게 제시하는가.", "max_score": 5},
        {"criteria": "이유/근거의 적절성", "description": "제시한 이유·근거가 주장과 논리적으로 타당하게 연결되는가.", "max_score": 5},
        {"criteria": "어문 규범과 관습", "description": "맞춤법·띄어쓰기 등 어문 규범을 지키는가.", "max_score": 5},
    ],
    "user_answer": (
        "로봇세는 도입해야 한다. 로봇의 발달로 일자리를 잃는 사람들이 늘고있기 때문에, "
        "이들을 지원할 재원이 필요하다. 반대하는 사람들은 로봇세가 기술 발전을 저해한다고 "
        "주장하지만, 세율을 낮게 책정하면 그 부작용은 최소화할 수 있다."
    ),
}

result = grading_app.invoke(state)

print("=== error ===")
print(result.get("error"))
print("=== criteria_scores ===")
print(json.dumps(result.get("criteria_scores"), ensure_ascii=False, indent=2))
print("=== total_score ===")
print(result.get("total_score"))
print("=== overall_comment ===")
print(result.get("overall_comment"))
