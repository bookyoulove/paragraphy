from types import SimpleNamespace


def test_rubric_generate_returns_llm_text(client, fake_claude):
    fake_claude.chat.return_value = SimpleNamespace(
        content="1. 항목 A (60점)\n2. 항목 B (40점)", tool_calls=None
    )
    res = client.post(
        "/api/rubric/generate",
        json={"title": "테스트 문제", "content": "문제 본문입니다."},
    )
    assert res.status_code == 200
    assert res.json()["rubric"] == "1. 항목 A (60점)\n2. 항목 B (40점)"

    # 프롬프트에 문제 본문이 실제로 포함되어 전달됐는지 확인
    _, kwargs = fake_claude.chat.call_args
    messages = fake_claude.chat.call_args.args[0] if fake_claude.chat.call_args.args else kwargs["messages"]
    joined = " ".join(m["content"] for m in messages)
    assert "문제 본문입니다." in joined
    assert "테스트 문제" in joined
