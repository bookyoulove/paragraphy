"""RAG 검색 어댑터.

벡터 저장소 구현은 그래프에서 분리한다. Chroma가 설치되지 않은 환경에서도
에이전트 패키지 자체와 LLM 그래프는 import할 수 있도록 실제 import는 최초
검색 시점에 지연한다.
"""

from __future__ import annotations

from importlib import import_module
from pathlib import Path
from typing import Any

from typing_extensions import TypedDict

PERSIST_DIR = Path(__file__).resolve().parents[3] / "chroma_data"
COLLECTION_NAME = "essay_grading_reference"


class RetrievedChunk(TypedDict):
    text: str
    metadata: dict[str, Any]
    distance: float


_client: Any = None


def _get_client() -> Any:
    global _client
    if _client is None:
        try:
            chromadb = import_module("chromadb")
        except ImportError as exc:
            raise RuntimeError("RAG를 사용하려면 chromadb를 설치하세요.") from exc
        PERSIST_DIR.mkdir(parents=True, exist_ok=True)
        _client = chromadb.PersistentClient(path=str(PERSIST_DIR))
    return _client


def get_collection() -> Any:
    return _get_client().get_or_create_collection(COLLECTION_NAME)


def query(
    query_text: str,
    *,
    n_results: int = 3,
    where: dict[str, Any] | None = None,
) -> list[RetrievedChunk]:
    collection = get_collection()
    if collection.count() == 0:
        return []
    result = collection.query(
        query_texts=[query_text], n_results=n_results, where=where
    )
    documents = (result.get("documents") or [[]])[0]
    metadatas = (result.get("metadatas") or [[]])[0]
    distances = (result.get("distances") or [[]])[0]
    return [
        RetrievedChunk(text=doc, metadata=dict(meta or {}), distance=distance)
        for doc, meta, distance in zip(documents, metadatas, distances)
    ]


def upsert_chunks(
    ids: list[str], texts: list[str], metadatas: list[dict[str, Any]]
) -> None:
    if ids:
        get_collection().upsert(ids=ids, documents=texts, metadatas=metadatas)


def reset_collection() -> None:
    try:
        _get_client().delete_collection(COLLECTION_NAME)
    except ValueError:
        pass
