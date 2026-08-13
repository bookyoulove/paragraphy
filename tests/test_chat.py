import json
from types import SimpleNamespace


def _setup_session_with_answer(client):
    user = client.post("/api/login", json={"identifier": "챗봇테스트"}).json()
    problem = client.get("/api/problems").json()[0]
    session = client.post(
        "/api/sessions",
        json={"user_id": user["id"], "problem_id": problem["id"], "problem_source": problem["source"]},
    ).json()
    client.post("/api/answers", json={"session_id": session["id"], "text": "테스트 답안", "status": "draft"})
    return session


def _fake_tool_call(call_id, name, arguments):
    return SimpleNamespace(
        id=call_id,
        function=SimpleNamespace(name=name, arguments=json.dumps(arguments)),
    )


def test_chat_requires_existing_session(client, fake_claude):
    res = client.post("/api/chat", json={"session_id": 99999, "text": "질문"})
    assert res.status_code == 404


def test_chat_without_tool_call_appends_two_messages(client, fake_claude):
    session = _setup_session_with_answer(client)
    fake_claude.chat.return_value = SimpleNamespace(content="단순 답변입니다.", tool_calls=None)

    res = client.post("/api/chat", json={"session_id": session["id"], "text": "안녕"})
    assert res.status_code == 200
    messages = res.json()["messages"]
    assert len(messages) == 2
    assert messages[0]["role"] == "user"
    assert messages[0]["text"] == "안녕"
    assert messages[1]["role"] == "assistant"
    assert messages[1]["text"] == "단순 답변입니다."


def test_chat_executes_tool_call_before_replying(client, fake_claude):
    """LLM이 get_feedback 도구를 호출하면, 실행 결과를 반영한 두 번째 응답을 반환해야 한다."""
    session = _setup_session_with_answer(client)

    tool_call_response = SimpleNamespace(
        content=None,
        tool_calls=[_fake_tool_call("call_1", "get_feedback", {})],
    )
    final_response = SimpleNamespace(content="아직 채점 결과가 없다는 걸 확인했습니다.", tool_calls=None)
    fake_claude.chat.side_effect = [tool_call_response, final_response]

    res = client.post("/api/chat", json={"session_id": session["id"], "text": "내 점수 알려줘"})
    assert res.status_code == 200
    messages = res.json()["messages"]
    assert messages[-1]["role"] == "assistant"
    assert messages[-1]["text"] == "아직 채점 결과가 없다는 걸 확인했습니다."
    assert fake_claude.chat.call_count == 2
