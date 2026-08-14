"""RAG 에이전트가 쓰는 벡터DB(Chroma) 접근 서비스.

국립국어원 채점 준거 상세/채점 사례, 경희대·한양대 채점 척도 해설처럼
"검색해서 근거로 인용할" 비정형 텍스트를 청크 단위로 저장/검색한다.
초기 단계라 임베딩은 Chroma 기본 임베딩 함수(로컬 ONNX MiniLM, API 키 불필요)를
쓴다 — 이후 AI Cloud 게이트웨이가 임베딩 API를 지원하면 이 파일만 바꾸면 된다.

Hybrid search/Reranker/HyDE 등 고도화는 다음 단계로 미루고, 지금은 구조만 잡는다
(원 기획서 4절 RAG 에이전트 설명 그대로).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, TypedDict

import chromadb

PERSIST_DIR = Path(__file__).resolve().parents[2] / "chroma_data"
COLLECTION_NAME = "essay_grading_reference"


class RetrievedChunk(TypedDict):
    text: str
    metadata: dict[str, Any]
    distance: float


_client: chromadb.ClientAPI | None = None


def _get_client() -> chromadb.ClientAPI:
    global _client
    if _client is None:
        PERSIST_DIR.mkdir(parents=True, exist_ok=True)
        _client = chromadb.PersistentClient(path=str(PERSIST_DIR))
    return _client


def get_collection():
    return _get_client().get_or_create_collection(COLLECTION_NAME)


def upsert_chunks(ids: list[str], texts: list[str], metadatas: list[dict[str, Any]]) -> None:
    """청크를 (재실행해도 중복 없이) upsert한다. id는 호출자가 결정적으로 생성해야 한다."""
    if not ids:
        return
    get_collection().upsert(ids=ids, documents=texts, metadatas=metadatas)  # type: ignore[arg-type]


def reset_collection() -> None:
    """전체 재색인 시 사용 (컬렉션을 지우고 새로 만든다)."""
    client = _get_client()
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass


def query(
    query_text: str,
    *,
    n_results: int = 3,
    where: dict[str, Any] | None = None,
) -> list[RetrievedChunk]:
    """query_text와 의미적으로 가까운 청크를 최대 n_results개 반환한다.

    where: Chroma 메타데이터 필터 (예: {"university": "경희대"}). None이면 전체 대상.
    """
    collection = get_collection()
    if collection.count() == 0:
        return []
    result = collection.query(query_texts=[query_text], n_results=n_results, where=where)
    documents = (result.get("documents") or [[]])[0]
    metadatas = (result.get("metadatas") or [[]])[0]
    distances = (result.get("distances") or [[]])[0]
    return [
        RetrievedChunk(text=doc, metadata=dict(meta or {}), distance=dist)
        for doc, meta, dist in zip(documents, metadatas, distances)
    ]
