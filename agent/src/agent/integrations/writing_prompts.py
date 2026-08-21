"""'분야별 논증적 글쓰기 문항' 코퍼스를 공용 RAG 컬렉션에 색인한다."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from agent.integrations import retrieval

logger = logging.getLogger(__name__)

SOURCE = "논증적_글쓰기_문항"
DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "writing_prompts.json"

_indexed = False


def load_items() -> list[dict[str, Any]]:
    with open(DATA_PATH, encoding="utf-8") as f:
        return json.load(f)


def ensure_indexed() -> None:
    """최초 1회, 코퍼스를 RAG 컬렉션에 upsert한다. 실패해도 예외를 올리지 않는다."""
    global _indexed
    if _indexed:
        return
    try:
        items = load_items()
        ids = [item["id"] for item in items]
        texts = [item["content"] for item in items]
        metadatas: list[dict[str, object]] = [
            {
                "source": SOURCE,
                "category": item["category"],
                "label": item["label"],
                "title": item["title"],
            }
            for item in items
        ]
        retrieval.upsert_chunks(ids, texts, metadatas)
        _indexed = True
    except Exception:
        logger.exception("Failed to index writing prompts corpus")
