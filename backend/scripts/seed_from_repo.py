"""`논술문서 텍스트/` 안의 정형 자료를 problems/rubrics 테이블로 시딩한다.

대상 (구조화된 자료만 — 비정형 근거자료는 3단계 벡터DB용으로 별도 처리):
  - 경희대 2025/2026: `*_문제와_지문.md` + `*_채점기준과_해설.md`
  - 한양대 2025/2026: `한양대 상경 {year} 문제.txt` + `... 평가기준.md` (+ `... 담안.txt`)
  - 국립국어원: `국립국어원_논술문항_및_채점기준.txt` (Q1~Q10 + 9개 준거)

재실행해도 중복 생성되지 않도록 (university, year, title) 자연키 기준 upsert.
모든 rubric은 max_score=5로 통일하고, 원본 배점은 description에 "[원배점 N점]"으로 남긴다.

실행:
    cd backend && .venv/Scripts/python scripts/seed_from_repo.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_DIR.parent
DOCS_DIR = REPO_ROOT / "논술문서 텍스트"

sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy.orm import Session  # noqa: E402

from app.core.db import Base, SessionLocal, engine  # noqa: E402
from app.models import Problem, Rubric  # noqa: E402
from app.services.doc_parsing import extract_section as _section  # noqa: E402

CIRCLED = "①②③④⑤⑥⑦⑧⑨⑩"


# ---------------------------------------------------------------------------
# 공통 upsert 헬퍼
# ---------------------------------------------------------------------------


def upsert_problem(
    db: Session,
    *,
    title: str,
    content: str,
    university: str | None,
    year: int | None,
    model_answer: str | None = None,
) -> Problem:
    existing = (
        db.query(Problem)
        .filter(Problem.title == title, Problem.university == university, Problem.year == year)
        .one_or_none()
    )
    if existing:
        existing.content = content
        existing.model_answer = model_answer
        problem = existing
    else:
        problem = Problem(
            title=title,
            content=content,
            university=university,
            year=year,
            model_answer=model_answer,
            created_by_user=False,
        )
        db.add(problem)
        db.flush()
    return problem


def upsert_rubrics(db: Session, problem: Problem, items: list[tuple[str, str]]) -> None:
    """items: [(criteria, description), ...]. 기존 problem의 rubric을 통째로 교체(delete+insert)한다."""
    db.query(Rubric).filter(Rubric.problem_id == problem.problem_id).delete()
    for criteria, description in items:
        db.add(Rubric(problem_id=problem.problem_id, criteria=criteria, description=description, max_score=5))


# ---------------------------------------------------------------------------
# 경희대: 문제와_지문.md + 채점기준과_해설.md
# ---------------------------------------------------------------------------

ROMAN = {"Ⅰ": "Ⅰ", "Ⅱ": "Ⅱ"}


def parse_kyunghee(year: int) -> list[dict]:
    problem_path = DOCS_DIR / f"{year}_경희대논술_문제와_지문.md"
    rubric_path = DOCS_DIR / f"{year}_경희대논술_채점기준과_해설.md"
    if not problem_path.exists() or not rubric_path.exists():
        print(f"  [skip] 경희대 {year}: 파일 없음")
        return []

    problem_text = problem_path.read_text(encoding="utf-8")
    rubric_text = rubric_path.read_text(encoding="utf-8")

    # 1) 논제 문장 (## 1. 문제 ~ ## 2. 지문)
    statements_block = _section(problem_text, "## 1. 문제", ["## 2. 지문"])
    statements: dict[str, str] = {}
    for m in re.finditer(r"^\d\)\s*\[?논제\s*(Ⅰ|Ⅱ)\]?[:\s]*(.+?)$", statements_block, re.MULTILINE):
        roman, stmt = m.group(1), m.group(2).strip()
        # 다음 논제 헤더 전까지 이어지는 줄바꿈된 문장도 포함
        statements[roman] = stmt

    # 지문 전체 (## 2. 지문 ~ 파일 끝)
    passages = _section(problem_text, "## 2. 지문", [])

    # 2) 모범 답안 (## 5. 모범 답안 ~ ## 6. 문제 해설)
    model_answers_block = _section(rubric_text, "## 5. 모범 답안", ["## 6. 문제 해설"])
    model_answers: dict[str, str] = {}
    parts = re.split(r"\*\*\[논제\s*(Ⅰ|Ⅱ|1|2|I|II)\]\*\*", model_answers_block)
    # parts = [prefix, label1, text1, label2, text2, ...]
    label_map = {"Ⅰ": "Ⅰ", "1": "Ⅰ", "I": "Ⅰ", "Ⅱ": "Ⅱ", "2": "Ⅱ", "II": "Ⅱ"}
    for i in range(1, len(parts), 2):
        label = label_map.get(parts[i], parts[i])
        model_answers[label] = parts[i + 1].strip()

    # 3) 채점 기준 (## 3. 채점 기준 ~ ## 4. 채점 척도)
    criteria_block = _section(rubric_text, "## 3. 채점 기준", ["## 4. 채점 척도"])
    results: list[dict] = []
    for roman in ("Ⅰ", "Ⅱ"):
        if roman not in statements:
            continue
        sub = _section(criteria_block, f"### [논제 {roman}]", [f"### [논제 {'Ⅱ' if roman == 'Ⅰ' else 'Ⅰ'}]"])
        if not sub:
            # 마지막 논제인 경우 다음 섹션 헤더가 없을 수 있음
            idx = criteria_block.find(f"### [논제 {roman}]")
            sub = criteria_block[idx:] if idx != -1 else ""

        rubric_items: list[tuple[str, str]] = []

        # 원고지 사용법 / 원고 분량 -> 형식 준수 항목 하나로 요약
        format_bits = []
        for label in ("**1) 원고지 사용법**", "**2) 원고 분량**"):
            block = _section(sub, label, ["**3) 내용평가**"])
            if block:
                format_bits.append(block.strip())
        if format_bits:
            rubric_items.append(("형식 및 분량 준수", " / ".join(format_bits)[:800] + " [원배점: 별도 배점 없음, 감점·가산 항목]"))

        # 내용평가 ①~④ 항목
        content_block = _section(sub, "**3) 내용평가**", [])
        for m in re.finditer(r"([①-⑩])\s*(.+?)\s*[—-]\s*(\d+)점", content_block):
            _, desc, point = m.groups()
            rubric_items.append((desc.strip()[:120], f"{desc.strip()} [원배점 {point}점]"))

        content = statements[roman]
        if passages:
            content += "\n\n[지문]\n" + passages

        problem = {
            "title": f"{year}년 경희대 논술 — 논제 {roman}",
            "content": content,
            "university": "경희대",
            "year": year,
            "model_answer": model_answers.get(roman),
            "rubrics": rubric_items,
        }
        results.append(problem)

    return results


# ---------------------------------------------------------------------------
# 한양대: 문제.txt + 평가기준.md (+ 담안.txt)
# ---------------------------------------------------------------------------


def parse_hanyang(year: int) -> dict | None:
    problem_path = DOCS_DIR / f"한양대 상경 {year} 문제.txt"
    rubric_path = DOCS_DIR / f"한양대 상경 {year} 평가기준.md"
    answer_path = DOCS_DIR / f"한양대 상경 {year} 담안.txt"
    if not problem_path.exists() or not rubric_path.exists():
        print(f"  [skip] 한양대 {year}: 파일 없음")
        return None

    content = problem_path.read_text(encoding="utf-8").strip()
    rubric_text = rubric_path.read_text(encoding="utf-8")
    model_answer = answer_path.read_text(encoding="utf-8").strip() if answer_path.exists() else None

    rubric_items: list[tuple[str, str]] = []
    for line in rubric_text.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 3:
            continue
        label, desc, point = cells[0], " ".join(cells[1:-1]), cells[-1]
        if not re.fullmatch(r"\d+", point):
            continue  # 헤더/구분선/종합점수(A-F) 테이블 등은 건너뜀
        label = label.lstrip("- ").strip()  # 표기상의 "- " 접두는 제거하되 행 자체는 유지
        desc = re.sub(r"<br\s*/?>", " ", desc).strip()
        rubric_items.append((label[:120], f"{desc}[원배점 {point}점]"))

    return {
        "title": f"{year}년 한양대 상경계열 논술",
        "content": content,
        "university": "한양대",
        "year": year,
        "model_answer": model_answer,
        "rubrics": rubric_items,
    }


# ---------------------------------------------------------------------------
# 국립국어원: Q1~Q10 + 9개 준거 (문제은행 기본 채점기준, 사용자 문제의 참고용 기본 항목)
# ---------------------------------------------------------------------------

GUKRIP_CRITERIA: list[tuple[str, str]] = [
    ("문제 상황 제시", "글이 다루는 문제 상황을 분명하게 제시하는가. [내용 범주, 5점 척도]"),
    ("다른 입장에 대한 고려", "자신의 주장과 다른 입장을 충분히 고려하는가. [내용 범주, 5점 척도]"),
    ("주장", "논제에 대한 자신의 주장을 명확하게 제시하는가. [내용 범주, 5점 척도]"),
    ("이유/근거의 적절성", "제시한 이유·근거가 주장과 논리적으로 타당하게 연결되는가. [내용 범주, 5점 척도]"),
    ("이유/근거의 충분성", "주장을 뒷받침하는 이유·근거를 충분히 제시하는가. [내용 범주, 5점 척도]"),
    ("글 전체 조직", "서론-본론-결론 등 글 전체의 구성이 유기적으로 조직되는가. [조직 범주, 5점 척도]"),
    ("문단 내 조직", "문단 내부의 문장들이 통일성·응집성 있게 조직되는가. [조직 범주, 5점 척도]"),
    ("문장과 어휘", "문장 구성과 어휘 선택이 정확하고 자연스러운가. [표현 범주, 5점 척도]"),
    ("어문 규범과 관습", "맞춤법·띄어쓰기 등 어문 규범과 쓰기 관습을 지키는가. [표현 범주, 5점 척도]"),
]


def parse_gukrip() -> list[dict]:
    path = DOCS_DIR / "국립국어원_논술문항_및_채점기준.txt"
    if not path.exists():
        print("  [skip] 국립국어원: 파일 없음")
        return []
    text = path.read_text(encoding="utf-8")

    results: list[dict] = []
    for m in re.finditer(r"\[Q(\d+)\]\s*(.+?)(?=\[Q\d+\]|=====|\Z)", text, re.DOTALL):
        qnum, body = m.group(1), m.group(2).strip()
        results.append(
            {
                "title": f"국립국어원 논증적 글쓰기 문항 Q{qnum}",
                "content": body,
                "university": "국립국어원",
                "year": None,
                "model_answer": None,
                "rubrics": GUKRIP_CRITERIA,
            }
        )
    return results


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def run() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    counts = {"problems": 0, "rubrics": 0}
    try:
        problem_dicts: list[dict] = []
        for year in (2025, 2026):
            problem_dicts.extend(parse_kyunghee(year))
            hy = parse_hanyang(year)
            if hy:
                problem_dicts.append(hy)
        problem_dicts.extend(parse_gukrip())

        for pd in problem_dicts:
            problem = upsert_problem(
                db,
                title=pd["title"],
                content=pd["content"],
                university=pd["university"],
                year=pd["year"],
                model_answer=pd["model_answer"],
            )
            upsert_rubrics(db, problem, pd["rubrics"])
            counts["problems"] += 1
            counts["rubrics"] += len(pd["rubrics"])
            print(f"  [ok] {pd['title']} — rubric {len(pd['rubrics'])}개")

        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    print(f"\n완료: problems {counts['problems']}건, rubrics {counts['rubrics']}건 upsert")


if __name__ == "__main__":
    run()