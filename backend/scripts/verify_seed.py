import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.db import SessionLocal
from app.models import Problem, Rubric

db = SessionLocal()
problems = db.query(Problem).order_by(Problem.university, Problem.year, Problem.title).all()
print(f"총 문제 수: {len(problems)}")
for p in problems:
    rubrics = db.query(Rubric).filter(Rubric.problem_id == p.problem_id).all()
    print("=" * 80)
    print(f"[{p.university} / {p.year}] {p.title}")
    print(f"  content 길이: {len(p.content)}자, model_answer: {'있음(' + str(len(p.model_answer)) + '자)' if p.model_answer else '없음'}")
    print(f"  content 앞부분: {p.content[:80]!r}")
    for r in rubrics:
        print(f"    - [{r.max_score}점] {r.criteria} :: {r.description[:70]!r}")
db.close()