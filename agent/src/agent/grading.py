"""채점 그래프의 호환 진입점.

새 코드는 ``agent.graphs.grading``를 사용한다.
"""

from agent.facade import AnalysisAgent
from agent.graphs.grading import build_grading_graph, grading_app

__all__ = ["AnalysisAgent", "build_grading_graph", "grading_app"]
