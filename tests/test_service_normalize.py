from backend.service import _normalize_grading_result, sum_scores


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
