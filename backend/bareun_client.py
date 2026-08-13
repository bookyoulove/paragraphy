"""Bareun(bareun.ai) 맞춤법/어문규정 검사 연동.

설계 원칙: 어문 오류 검출은 문제 출처(대학/국립국어원/사용자입력)와 무관하게
공통으로 처리한다 (Grading Agent가 아니라 별도 규칙 기반 서비스가 담당).
"""

from typing import Any, Dict, List

from .config import settings

_CATEGORY_LABELS = {
    "GRAMMER": "문법",
    "WORD": "어휘",
    "SPACING": "띄어쓰기",
    "STANDARD": "표준어",
    "TYPO": "오타",
    "FOREIGN_WORD": "외래어 표기",
    "CONFUSABLE_WORDS": "혼동 어휘",
    "SENTENCE": "문장 부호",
}

_corrector = None
_unavailable_reason = None


def _get_corrector():
    global _corrector, _unavailable_reason
    if _corrector is not None or _unavailable_reason is not None:
        return _corrector
    try:
        from bareunpy import Corrector

        if not settings.bareun_api_key:
            _unavailable_reason = "BAREUN_API_KEY가 설정되지 않았습니다."
            return None
        _corrector = Corrector(apikey=settings.bareun_api_key)
        return _corrector
    except Exception as exc:  # pragma: no cover - defensive
        _unavailable_reason = str(exc)
        return None


def check_spelling(text: str) -> List[Dict[str, Any]]:
    """Bareun 맞춤법/어문규정 검사 결과를 grammar_errors 스키마로 변환한다.

    Bareun 연동이 불가능하면(키 미설정, 네트워크 오류 등) 조용히 빈 목록을 반환한다 —
    Grading Agent가 LLM 자체 판단으로 이 공백을 채운다.
    """
    corrector = _get_corrector()
    if corrector is None or not text.strip():
        return []

    try:
        response = corrector.correct_error(text)
    except Exception:
        return []

    helps = response.helps  # protobuf map<string, HelpInfo>
    errors: List[Dict[str, Any]] = []
    for block in response.revised_blocks:
        for revision in block.revisions:
            if not block.origin.content or block.origin.content == revision.revised:
                continue  # 실제 변경이 없는 오탐(사전 미등재 단어 등)은 제외
            category = _CATEGORY_LABELS.get(
                pb_category_name(revision.category), "어문 규범"
            )
            help_entry = helps.get(revision.help_id)
            note = help_entry.comment.strip().split("\n")[0] if help_entry else ""
            if not note:
                note = "한국어 어문 규정에 따른 교정입니다."
            errors.append(
                {
                    "type": category,
                    "before": block.origin.content,
                    "after": revision.revised,
                    "note": note,
                    "source": "bareun",
                }
            )
    return errors[:8]


def pb_category_name(value: int) -> str:
    import bareunpy.bareun.revision_service_pb2 as pb

    try:
        return pb.RevisionCategory.Name(value)
    except Exception:
        return "UNKNOWN"
