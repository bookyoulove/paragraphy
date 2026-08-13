from backend.seed_data import build_seed_problems


def test_build_seed_problems_returns_expected_sources():
    problems = build_seed_problems()
    assert len(problems) == 5
    sources = [p["source"] for p in problems]
    assert sources.count("한양대") == 2
    assert sources.count("경희대") == 2
    assert sources.count("국립국어원") == 1


def test_build_seed_problems_all_have_content_and_rubric():
    for p in build_seed_problems():
        assert p["content"].strip()
        assert p["rubric"].strip()
        assert p["meta"]["school"]


def test_nikl_problem_uses_nine_criteria_rubric():
    nikl = next(p for p in build_seed_problems() if p["source"] == "국립국어원")
    for label in ["문제 상황 제시", "주장", "이유·근거의 적절성", "글 전체 조직", "어문 규범과 관습"]:
        assert label in nikl["rubric"]
