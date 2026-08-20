"""bareun.ai 맞춤법 검사 연동 어댑터.

bareunpy는 protobuf 메시지를 반환한다. 이 모듈에서 SDK 전용 메시지를
``shared.schema.grammar.GrammarResult``로 변환해, 에이전트와 백엔드가 SDK의
구체적인 응답 타입에 의존하지 않도록 한다.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from importlib import import_module
from typing import Any

from shared.schema.grammar import (
    CleanUpPosition,
    CleanUpRange,
    CustomDictPos,
    GrammarResult,
    RevisedBlock,
    RevisedSentence,
    ReviseHelp,
    Revision,
    RevisionCategory,
)

from agent.retry import call_with_retry


@dataclass(frozen=True, slots=True)
class Correction:
    """화면의 교정 목록에 필요한 축약 표현."""

    original: str
    revised: str
    category: str
    comment: str


class SpellingIntegrationError(RuntimeError):
    """bareun.ai 호출 또는 응답 변환 실패."""


def _empty_result(text: str) -> GrammarResult:
    return GrammarResult(
        origin=text,
        revised=text,
        revised_blocks=[],
        whitespace_cleanup_ranges=[],
        revised_sentences=[],
        helps={},
        language="ko",
        tokens_count=0,
    )


@lru_cache(maxsize=1)
def _get_corrector() -> Any:
    try:
        bareunpy = import_module("bareunpy")
    except ImportError as exc:
        raise SpellingIntegrationError(
            "맞춤법 검사를 사용하려면 bareunpy를 설치하세요."
        ) from exc

    api_key = os.getenv("BAREUN_API_KEY")
    if not api_key:
        raise SpellingIntegrationError(
            "BAREUN_API_KEY가 설정되지 않았습니다. .env를 확인하세요."
        )
    return bareunpy.Corrector(
        apikey=api_key,
        host=os.getenv("BAREUN_HOST", "api.bareun.ai"),
        port=int(os.getenv("BAREUN_PORT", "443")),
    )


# bareun.ai가 붙이는 신뢰도 점수 기준. 점수가 낮은 후보는 "되으로써"처럼 문법적으로
# 성립하지 않는 추천을 포함하는 경우가 관찰되어 걸러낸다. 다만 SPACING(띄어쓰기)은
# 점수가 낮게 나와도 규칙 기반이라 신뢰도가 높으므로 예외로 둔다.
MIN_REVISION_SCORE = 0.5


def _convert_block(block: Any) -> RevisedBlock:
    # Corrector의 Python 응답은 origin을 str로 노출한다. 저수준 protobuf 응답처럼
    # TextSpan으로 노출되는 버전도 받아 shared 계약의 문자열로 정규화한다.
    origin = block.origin if isinstance(block.origin, str) else block.origin.content
    revisions = [
        Revision(
            revised=item.revised,
            score=item.score,
            category=RevisionCategory(item.category),
            help_id=item.help_id,
        )
        for item in block.revisions
        if item.score >= MIN_REVISION_SCORE
        or RevisionCategory(item.category) is RevisionCategory.SPACING
    ]
    return RevisedBlock(
        origin=origin,
        revised=block.revised if revisions else origin,
        revisions=revisions,
        nested=[_convert_block(item) for item in block.nested],
        lemma=block.lemma,
        pos=CustomDictPos(block.pos),
    )


def _convert_response(response: Any) -> GrammarResult:
    try:
        helps = {
            key: ReviseHelp(
                id=value.id,
                category=RevisionCategory(value.category),
                comment=value.comment,
                examples=list(value.examples),
                rule_article=value.rule_article,
            )
            for key, value in response.helps.items()
        }
        return GrammarResult(
            origin=response.origin,
            revised=response.revised,
            revised_blocks=[_convert_block(block) for block in response.revised_blocks],
            whitespace_cleanup_ranges=[
                CleanUpRange(
                    offset=item.offset,
                    length=item.length,
                    position=CleanUpPosition(item.position),
                )
                for item in response.whitespace_cleanup_ranges
            ],
            revised_sentences=[
                RevisedSentence(origin=item.origin, revised=item.revised)
                for item in response.revised_sentences
            ],
            helps=helps,
            language=response.language,
            tokens_count=response.tokens_count,
        )
    except (TypeError, ValueError, AttributeError, KeyError) as exc:
        raise SpellingIntegrationError(f"bareun.ai 응답 변환 실패: {exc}") from exc


def check_spelling(text: str) -> GrammarResult:
    """텍스트를 검사해 공용 ``GrammarResult``를 반환한다."""
    if not text or not text.strip():
        return _empty_result(text)

    try:
        corrector = _get_corrector()
        response = call_with_retry(
            lambda: corrector.correct_error(content=text),
            operation_name="Bareun spelling API",
            max_wait=8,
        )
        return _convert_response(response)
    except SpellingIntegrationError:
        raise
    except Exception as exc:
        raise SpellingIntegrationError(f"bareun.ai 호출 실패: {exc}") from exc


def derive_corrections(result: GrammarResult) -> list[Correction]:
    """공용 문법 결과에서 UI용 교정 항목을 파생한다."""
    corrections: list[Correction] = []
    for block in result.revised_blocks:
        if block.origin == block.revised:
            continue
        for revision in block.revisions:
            help_info = result.helps.get(revision.help_id)
            corrections.append(
                Correction(
                    original=block.origin,
                    revised=revision.revised,
                    category=revision.category.name,
                    comment=help_info.comment if help_info else "",
                )
            )
    return corrections
