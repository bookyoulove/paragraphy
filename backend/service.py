import json
from typing import Dict, Any, List
from .llm_client import ClaudeClient
from .models import AnalysisResult


def format_score_items(analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
    items = []
    rubric_elements = [
        ("내용", analysis.get("content_score", 16)),
        ("조직", analysis.get("structure_score", 14)),
        ("표현", analysis.get("expression_score", 15)),
        ("논리성", analysis.get("logic_score", 13)),
        ("완성도", analysis.get("completion_score", 15)),
    ]
    for label, value in rubric_elements:
        items.append({"label": f"{label}", "value": value, "total": 20})
    return items


def parse_grammar_errors(raw: str) -> List[Dict[str, Any]]:
    # Basic placeholder parser: split by line and categorize
    entries = []
    for line in raw.splitlines():
        if not line.strip():
            continue
        parts = line.split("|")
        if len(parts) >= 3:
            entries.append({"type": parts[0].strip(), "error": parts[1].strip(), "suggestion": parts[2].strip()})
        else:
            entries.append({"type": "grammar", "error": line.strip(), "suggestion": ""})
    return entries


async def grade_answer(session_id: int, text: str) -> Dict[str, Any]:
    client = ClaudeClient()
    prompt = (
        "당신은 한국 고등학교 국어 논술 채점관입니다. 다음 답안을 평가하여 점수와 첨삭 내용을 JSON 형식으로 반환하세요.\n\n"
        f"답안:\n{text}\n\n"
        "출력 포맷:\n"
        "{\n"
        "  \"score\": integer,\n"
        "  \"commentary\": string,\n"
        "  \"content_score\": integer,\n"
        "  \"structure_score\": integer,\n"
        "  \"expression_score\": integer,\n"
        "  \"logic_score\": integer,\n"
        "  \"completion_score\": integer,\n"
        "  \"grammar_errors\": [\n"
        "    {\"type\": \"string\", \"error\": \"string\", \"suggestion\": \"string\"}\n"
        "  ]\n"
        "}\n"
    )
    raw = await client.complete(prompt, max_tokens=800)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        data = {"score": 70, "commentary": raw, "content_score": 16, "structure_score": 14, "expression_score": 15, "logic_score": 13, "completion_score": 15, "grammar_errors": []}

    data["scores"] = format_score_items(data)
    if isinstance(data.get("grammar_errors"), str):
        data["grammar_errors"] = parse_grammar_errors(data["grammar_errors"])
    return data
