"""실제 논술 문서(`논술문서 텍스트/`)를 파싱하여 Problem 시드 데이터를 구축한다."""

from .config import BASE_DIR
from .rubrics import nikl_rubric_text

DOCS_DIR = BASE_DIR / "논술문서 텍스트"

NIKL_ROBOT_TAX_PROMPT = (
    "로봇의 발달로 일자리가 줄어들 것이라는 사람들의 불안이 커지면서 최근 로봇세 도입에 대한 논의가 활발하다. "
    "로봇세는 로봇의 노동으로 생산하는 경제적 가치에 부과하는 세금이다. 로봇 기술의 발달로 인해 일자리를 잃는 "
    "사람들이 갈수록 많아질 수 있기 때문에, 그런 사람들을 지원하거나 사회 안전망을 구축하기 위해 예산을 마련하자는 "
    "것이 로봇세 도입의 목적이다.\n\n"
    "[문항] 로봇세 도입에 대한 자신의 의견을 논리적으로 제시하는 글을 쓰시오.\n"
    "[유의 사항] 서론, 본론, 결론을 갖춘 완결된 글을 쓸 것(제목 쓰지 말 것). "
    "분량: 1,000자 내외(±200자, 공백 포함), 시간: 90분."
)


def _read(name: str) -> str:
    path = DOCS_DIR / name
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8").strip()


# 대학 공식 채점 기준(한양대/경희대)에는 어문 규정 오류에 대한 별도 배점 항목이 없다
# (원고지 사용법/어문 규정은 "채점위원 재량 감점" 정도로만 언급됨). 국립국어원 기준에는
# 이미 "어문 규범과 관습" 준거가 있으므로 이 노트를 붙이지 않는다.
GRAMMAR_CRITERION_LABEL = "문법과 어휘 (맞춤법·어법 정확성)"
GRAMMAR_CRITERION_NOTE = (
    "\n\n[플랫폼 공통 채점 항목]\n"
    f"- {GRAMMAR_CRITERION_LABEL} (1~5점): 위 공식 채점 기준에는 어문 규정 오류에 대한 별도 배점이 "
    "없어, 본 플랫폼이 모든 문제에 공통으로 적용하는 항목입니다. Bareun 어문규정 검사 결과를 "
    "기반으로 자동 채점됩니다."
)


def _with_grammar_criterion(rubric_text: str) -> str:
    if not rubric_text or GRAMMAR_CRITERION_LABEL in rubric_text:
        return rubric_text
    return rubric_text + GRAMMAR_CRITERION_NOTE


def build_seed_problems() -> list[dict]:
    problems = [
        dict(
            title="한양대 상경 논술 2025",
            source="한양대",
            content=_read("한양대 상경 2025 문제.txt"),
            rubric=_with_grammar_criterion(_read("한양대 상경 2025 평가기준.md")),
            model_answer=_read("한양대 상경 2025 담안.txt"),
            meta={"school": "한양대", "exam_type": "상경계열", "year": "2025", "category": "대학논술"},
        ),
        dict(
            title="한양대 상경 논술 2026",
            source="한양대",
            content=_read("한양대 상경 2026 문제.txt"),
            rubric=_with_grammar_criterion(_read("한양대 상경 2026 평가기준.md")),
            model_answer=_read("한양대 상경 2026 담안.txt"),
            meta={"school": "한양대", "exam_type": "상경계열", "year": "2026", "category": "대학논술"},
        ),
        dict(
            title="경희대 사회계 논술 2025",
            source="경희대",
            content=_read("2025_경희대논술_문제와_지문.md"),
            rubric=_with_grammar_criterion(_read("2025_경희대논술_채점기준과_해설.md")),
            model_answer=None,
            meta={"school": "경희대", "exam_type": "사회계열", "year": "2025", "category": "대학논술"},
        ),
        dict(
            title="경희대 사회계 논술 2026",
            source="경희대",
            content=_read("2026_경희대논술_문제와_지문.md"),
            rubric=_with_grammar_criterion(_read("2026_경희대논술_채점기준과_해설.md")),
            model_answer=None,
            meta={"school": "경희대", "exam_type": "인문계열", "year": "2026", "category": "대학논술"},
        ),
        dict(
            title="국립국어원 논증적 글쓰기 — 로봇세 도입",
            source="국립국어원",
            content=NIKL_ROBOT_TAX_PROMPT,
            rubric=nikl_rubric_text(),
            model_answer=None,
            meta={"school": "국립국어원", "exam_type": "논증적 글쓰기", "year": "2025", "category": "국어"},
        ),
    ]
    # 문서가 비어있는 경우(경로 문제 등) 시드에서 제외해 깨진 문제 카드가 노출되지 않게 한다.
    return [p for p in problems if p["content"]]
