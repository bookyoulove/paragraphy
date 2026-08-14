"""bareun.ai 맞춤법 검사 API 연동 서비스.

문법/표현 첨삭 에이전트와 채점/루브릭 에이전트(어문규정 항목 채점)가
공통으로 이 모듈의 `check_spelling()` 하나만 호출하도록 한다.
Corrector 인스턴스화 등 bareun SDK 세부 사항은 이 파일 안에 캡슐화한다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache

from bareunpy import Corrector
from bareunpy.bareun.revision_service_pb2 import RevisionCategory

from app.core.config import settings


@dataclass
class Correction:
    """개별 교정 항목 하나."""

    original: str  # 교정 전 어절/구간
    revised: str  # 교정 후 어절/구간
    category: str  # bareun이 분류한 오류 유형 (예: 맞춤법, 띄어쓰기 등)
    comment: str  # 교정 사유 설명


@dataclass
class SpellingResult:
    """맞춤법 검사 결과."""

    origin: str  # 원문 전체
    revised: str  # 교정문 전체
    corrections: list[Correction] = field(default_factory=list)


class SpellingServiceError(RuntimeError):
    """bareun API 호출 실패 시 발생."""


@lru_cache(maxsize=1)
def _get_corrector() -> Corrector:
    if not settings.bareun_api_key:
        raise SpellingServiceError(
            "BAREUN_API_KEY가 설정되지 않았습니다. 프로젝트 루트 .env를 확인하세요."
        )
    return Corrector(
        apikey=settings.bareun_api_key,
        host=settings.bareun_host,
        port=settings.bareun_port,
    )


def check_spelling(text: str) -> SpellingResult:
    """essay 텍스트를 bareun.ai로 교정하고 구조화된 결과를 반환한다.

    Args:
        text: 검사할 원문 (에세이 전체 또는 문단 단위).

    Returns:
        SpellingResult: 원문/교정문/교정 항목 리스트.

    Raises:
        SpellingServiceError: API 키 미설정 또는 호출 실패 시.
    """
    if not text or not text.strip():
        return SpellingResult(origin=text, revised=text, corrections=[])

    corrector = _get_corrector()
    try:
        response = corrector.correct_error(content=text)
    except Exception as exc:  # bareun/grpc 예외를 서비스 레이어 예외로 통일
        raise SpellingServiceError(f"bareun.ai 호출 실패: {exc}") from exc

    # help_id -> 교정 사유(카테고리/코멘트) 매핑
    helps = {key: value for key, value in response.helps.items()}

    corrections: list[Correction] = []
    for block in response.revised_blocks:
        # block.origin은 TextSpan(content, begin_offset, length) 메시지
        origin_text = block.origin.content
        if origin_text == block.revised:
            continue  # 실제 변경이 없는 블록은 건너뜀
        for revision in block.revisions:
            help_info = helps.get(revision.help_id)
            category_name = RevisionCategory.Name(revision.category)
            corrections.append(
                Correction(
                    original=origin_text,
                    revised=revision.revised,
                    category=category_name,
                    comment=help_info.comment if help_info else "",
                )
            )

    return SpellingResult(
        origin=response.origin,
        revised=response.revised,
        corrections=corrections,
    )


if __name__ == "__main__":
    # 스모크 테스트: 실제 API 키로 샘플 문장 하나가 정상 교정되는지 확인.
    sample = "나는 오늘 학교에 갔다왔다. 그리고 밥을먹었습니다. 안녕하세요 반갑습니다.."
    result = check_spelling(sample)
    print("=== 원문 ===")
    print(result.origin)
    print("=== 교정문 ===")
    print(result.revised)
    print("=== 교정 항목 ===")
    if not result.corrections:
        print("(감지된 교정 항목 없음)")
    for c in result.corrections:
        print(f"- [{c.category}] '{c.original}' -> '{c.revised}' ({c.comment})")