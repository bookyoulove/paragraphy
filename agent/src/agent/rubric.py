"""루브릭 그래프의 호환 진입점.

새 코드는 ``agent.graphs.rubric``를 사용한다. 이 모듈은 기존 통합 코드가
``agent.rubric.rubric_app``를 참조하는 동안의 점진적 이전을 위해 남겨둔다.
"""

from agent.facade import RubricAgent
from agent.graphs.rubric import build_rubric_graph, rubric_app

__all__ = ["RubricAgent", "build_rubric_graph", "rubric_app"]
