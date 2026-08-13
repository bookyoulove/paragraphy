from backend.service import _apply_grammar_score, _normalize_grading_result, sum_scores


def test_normalize_grading_result_happy_path():
    data = {
        "scores": [
            {"label": "A", "value": 4, "max_score": 5},
            {"label": "B", "value": 3, "max_score": 5},
        ],
        "commentary": "총평",
        "suggestions": ["제안1", "제안2", "제안3", "제안4", "제안5", "제안6"],
        "grammar_errors": [{"type": "t", "before": "b", "after": "a", "note": "n"}],
    }
    result = _normalize_grading_result(data)
    assert result["score"] == 7
    assert result["total_max"] == 10
    assert len(result["scores"]) == 2
    # suggestions는 최대 5개로 잘려야 한다
    assert len(result["suggestions"]) == 5


def test_normalize_grading_result_handles_missing_fields():
    result = _normalize_grading_result({})
    assert result["score"] == 0
    assert result["total_max"] == 100  # 배점 정보가 전혀 없으면 100점 만점으로 폴백
    assert result["scores"] == []
    assert result["grammar_errors"] == []


def test_normalize_grading_result_caps_grammar_errors_at_five():
    data = {
        "scores": [],
        "grammar_errors": [{"type": "t", "before": str(i), "after": str(i), "note": ""} for i in range(10)],
    }
    result = _normalize_grading_result(data)
    assert len(result["grammar_errors"]) == 5


def test_sum_scores_empty_falls_back_to_100():
    value, total = sum_scores(None)
    assert (value, total) == (0, 100)


def test_sum_scores_sums_correctly():
    value, total = sum_scores([{"value": 3, "max_score": 5}, {"value": 2, "max_score": 5}])
    assert (value, total) == (5, 10)


def test_apply_grammar_score_appends_when_missing():
    """채점 기준에 어문/맞춤법 관련 준거가 없으면 새 항목으로 추가되어야 한다."""
    result = {"score": 4, "total_max": 5, "scores": [{"label": "구성과 전개", "value": 4, "max_score": 5}]}
    _apply_grammar_score(result, bareun_errors=[])
    assert len(result["scores"]) == 2
    assert result["scores"][-1] == {"label": "문법과 어휘 (맞춤법·어법 정확성)", "value": 5, "max_score": 5}
    assert result["score"] == 9
    assert result["total_max"] == 10


def test_apply_grammar_score_overrides_existing_criterion():
    """LLM이 이미 어문 관련 준거를 채점했더라도, Bareun 결과 값으로 덮어써야 한다 (중복 추가 금지)."""
    result = {
        "score": 9,
        "total_max": 10,
        "scores": [
            {"label": "주장", "value": 4, "max_score": 5},
            {"label": "어문 규범과 관습", "value": 5, "max_score": 5},  # LLM의 임의 추정값
        ],
    }
    bareun_errors = [{"type": "맞춤법", "before": "됬다", "after": "됐다", "note": ""}] * 3
    _apply_grammar_score(result, bareun_errors)
    assert len(result["scores"]) == 2  # 새 항목이 추가되지 않고 기존 항목이 그대로 덮어써짐
    assert result["scores"][1]["value"] == 3  # 오류 2~3건 구간 → 3점
    assert result["score"] == 7  # 4 + 3
    assert result["total_max"] == 10


def test_apply_grammar_score_buckets_by_error_count():
    cases = [(0, 5), (1, 4), (3, 3), (5, 2), (6, 1)]
    for count, expected_value in cases:
        result = {"score": 0, "total_max": 0, "scores": []}
        errors = [{"type": "t", "before": "b", "after": "a", "note": ""}] * count
        _apply_grammar_score(result, errors)
        assert result["scores"][0]["value"] == expected_value, f"count={count}"
