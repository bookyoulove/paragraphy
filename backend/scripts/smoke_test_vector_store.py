"""vector_store 검색 스모크 테스트."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services import vector_store  # noqa: E402

queries = [
    ("다른 입장을 전혀 고려하지 않고 자기 주장만 반복하는 답안은 어떻게 채점해야 하나?", None),
    ("경희대 논술에서 제시문을 그대로 베껴쓰면 감점되나?", {"university": "경희대"}),
    ("어문 규범과 관습 채점 기준", {"rubric_item": "어문 규범과 관습"}),
]

for q, where in queries:
    print(f"\n=== 질의: {q!r} (필터: {where}) ===")
    results = vector_store.query(q, n_results=2, where=where)
    if not results:
        print("  (검색 결과 없음)")
    for r in results:
        print(f"  distance={r['distance']:.4f} meta={r['metadata']}")
        print(f"  text: {r['text'][:200]!r}")
