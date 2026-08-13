"""Bareun 연동의 오탐(false positive) 필터링 로직 검증.

실제 Bareun 서버에 네트워크 호출을 하지 않고, bareunpy가 반환하는 것과 동일한
구조의 protobuf 응답 객체를 직접 구성해 `check_spelling`의 필터링/변환 로직만 검증한다.
"""

import bareunpy.bareun.revision_service_pb2 as pb

from backend import bareun_client
from backend.bareun_client import check_spelling


class _FakeCorrector:
    def __init__(self, response):
        self._response = response

    def correct_error(self, text):
        return self._response


def _build_response(entries):
    """entries: list of (origin, revised, category, help_id, comment)"""
    response = pb.CorrectErrorResponse()
    for origin, revised, category, help_id, comment in entries:
        block = response.revised_blocks.add()
        block.origin.content = origin
        revision = block.revisions.add()
        revision.revised = revised
        revision.category = category
        revision.help_id = help_id
        if comment:
            response.helps[help_id].id = help_id
            response.helps[help_id].comment = comment
    return response


def test_check_spelling_filters_noop_corrections(monkeypatch):
    """before == after (실제 변경이 없는) 항목은 사전 미등재 고유명사 등에 대한
    오탐일 가능성이 높으므로 결과에서 제외되어야 한다."""
    response = _build_response(
        [
            ("확증편향을", "확증 편향을", pb.RevisionCategory.SPACING, "h1", "띄어쓰기 규정"),
            ("로봇세는", "로봇세는", pb.RevisionCategory.TYPO, "h2", "오타 의심"),  # no-op → 필터링 대상
        ]
    )
    monkeypatch.setattr(bareun_client, "_get_corrector", lambda: _FakeCorrector(response))

    errors = check_spelling("로봇세는 확증편향을 강화한다.")

    assert len(errors) == 1
    assert errors[0]["before"] == "확증편향을"
    assert errors[0]["after"] == "확증 편향을"
    assert errors[0]["type"] == "띄어쓰기"
    assert errors[0]["source"] == "bareun"


def test_check_spelling_filters_empty_origin(monkeypatch):
    response = _build_response(
        [("", "무언가", pb.RevisionCategory.WORD, "h1", "설명")]
    )
    monkeypatch.setattr(bareun_client, "_get_corrector", lambda: _FakeCorrector(response))
    assert check_spelling("텍스트") == []


def test_check_spelling_maps_known_categories_to_korean_labels(monkeypatch):
    response = _build_response(
        [
            ("얇어서", "얇아서", pb.RevisionCategory.GRAMMER, "h1", "모음조화 규정"),
            ("노출시켜", "노출해", pb.RevisionCategory.STANDARD, "h2", "표준어 규정"),
        ]
    )
    monkeypatch.setattr(bareun_client, "_get_corrector", lambda: _FakeCorrector(response))

    errors = check_spelling("텍스트")
    types = {e["before"]: e["type"] for e in errors}
    assert types["얇어서"] == "문법"
    assert types["노출시켜"] == "표준어"


def test_check_spelling_falls_back_to_default_note_when_help_missing(monkeypatch):
    response = _build_response(
        [("잘못된단어", "고친단어", pb.RevisionCategory.WORD, "missing_help_id", None)]
    )
    monkeypatch.setattr(bareun_client, "_get_corrector", lambda: _FakeCorrector(response))

    errors = check_spelling("텍스트")
    assert len(errors) == 1
    assert errors[0]["note"] == "한국어 어문 규정에 따른 교정입니다."


def test_check_spelling_caps_results_at_eight(monkeypatch):
    entries = [
        (f"원문{i}", f"수정{i}", pb.RevisionCategory.TYPO, f"h{i}", "설명")
        for i in range(12)
    ]
    response = _build_response(entries)
    monkeypatch.setattr(bareun_client, "_get_corrector", lambda: _FakeCorrector(response))

    errors = check_spelling("텍스트")
    assert len(errors) == 8


def test_check_spelling_returns_empty_when_corrector_unavailable(monkeypatch):
    monkeypatch.setattr(bareun_client, "_get_corrector", lambda: None)
    assert check_spelling("아무 텍스트") == []


def test_check_spelling_returns_empty_for_blank_text(monkeypatch):
    # 코렉터를 호출조차 하지 않아야 한다 (불필요한 네트워크 호출 방지)
    calls = []
    monkeypatch.setattr(
        bareun_client, "_get_corrector", lambda: calls.append("called") or _FakeCorrector(_build_response([]))
    )
    assert check_spelling("   ") == []
    assert calls == []
