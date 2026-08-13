"""`논술문서 텍스트/` 안의 비정형 근거자료를 청크+임베딩해 벡터DB(Chroma)에 적재한다.

대상 (1단계에서 SQLite로 옮기지 않고 남겨둔 것들 — RAG 에이전트가 채점 근거로 검색할
"검색해서 인용할" 텍스트):
  - 국립국어원 상세 자료 3종: 척도표(원자료), 준거설명(9개 준거 정의+척도+예시글 다수),
    실제채점사례(준거별 실제 점수+근거)
  - 경희대 2025/2026 채점기준과_해설.md의 "채점 척도"(항목별 가점 척도 상세) + "문제 해설"
    (SQLite rubrics.description엔 짧은 항목명+배점만 있고, 이 서술형 해설이 훨씬 풍부함)
  - 한양대 2025/2026 평가기준.md의 "출제 의도 및 문제 해설"

각 청크는 (source/university/year/doc_type/rubric_item) 메타데이터를 붙여, 채점 시
"어느 대학·어느 항목 기준으로 검색할지" 필터링할 수 있게 한다.

재실행 시 매번 컬렉션을 초기화하고 다시 채운다(청크 수/경계가 바뀔 수 있어 upsert만으로는
이전 실행의 잔여 청크가 남을 수 있음 — 코퍼스가 작아 전체 재색인 비용이 낮음).

실행:
    cd backend && .venv/Scripts/python scripts/build_vector_index.py
"""

from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path
from typing import Any, NamedTuple

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_DIR.parent
DOCS_DIR = REPO_ROOT / "논술문서 텍스트"

sys.path.insert(0, str(BACKEND_DIR))

from app.services import vector_store  # noqa: E402
from app.services.doc_parsing import chunk_text, extract_section  # noqa: E402

CRITERIA_NAMES = [
    "문제 상황 제시",
    "다른 입장에 대한 고려",
    "주장",
    "이유/근거의 적절성",
    "이유/근거의 충분성",
    "글 전체 조직",
    "문단 내 조직",
    "문장과 어휘",
    "어문 규범과 관습",
]

HEADER_RE = re.compile(r"=+\n(.+?)\n=+", re.MULTILINE)


class ChunkRecord(NamedTuple):
    id_key: str  # 사람이 읽을 수 있는 고유 키 (해시해서 chroma id로 사용, metadata에도 남김)
    text: str
    metadata: dict[str, Any]


def detect_rubric_item(text: str) -> str | None:
    for name in CRITERIA_NAMES:
        if name in text:
            return name
    return None


def split_by_fenced_headers(text: str) -> list[tuple[str, str]]:
    """`===\\n헤더\\n===` 로 감싸인 절 구분을 기준으로 (헤더, 본문) 목록을 반환."""
    matches = list(HEADER_RE.finditer(text))
    sections: list[tuple[str, str]] = []
    if matches:
        preamble = text[: matches[0].start()].strip()
        if preamble:
            sections.append(("(서두)", preamble))
    for i, m in enumerate(matches):
        header = m.group(1).strip()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        if body:
            sections.append((header, body))
    return sections


# ---------------------------------------------------------------------------
# 국립국어원 상세 자료 3종
# ---------------------------------------------------------------------------

GUKRIP_DETAIL_FILES = [
    ("척도표", "글쓰기채점_문항_예시글_채점기준표_척도.txt"),
    ("준거설명", "쓰기채점_준거설명_예시글_구조분석.txt"),
    ("채점사례", "쓰기채점_실제채점사례_점수와근거.txt"),
]


def load_gukrip_chunks() -> list[ChunkRecord]:
    records: list[ChunkRecord] = []
    for doc_type, filename in GUKRIP_DETAIL_FILES:
        path = DOCS_DIR / filename
        if not path.exists():
            print(f"  [skip] {filename}: 파일 없음")
            continue
        text = path.read_text(encoding="utf-8")
        for header, body in split_by_fenced_headers(text):
            rubric_item = detect_rubric_item(header) or detect_rubric_item(body[:300])
            for i, chunk in enumerate(chunk_text(body, max_chars=900)):
                metadata: dict[str, Any] = {
                    "source": "국립국어원",
                    "doc_type": doc_type,
                    "file": filename,
                    "section": header[:100],
                }
                if rubric_item:
                    metadata["rubric_item"] = rubric_item
                records.append(
                    ChunkRecord(
                        id_key=f"gukrip::{filename}::{header}::{i}",
                        text=f"[{header}]\n{chunk}",
                        metadata=metadata,
                    )
                )
        print(f"  [ok] {filename} ({doc_type})")
    return records


# ---------------------------------------------------------------------------
# 경희대: 채점기준과_해설.md의 "채점 척도"(상세 가점 기술) + "문제 해설"
# ---------------------------------------------------------------------------


def load_kyunghee_chunks() -> list[ChunkRecord]:
    records: list[ChunkRecord] = []
    for year in (2025, 2026):
        path = DOCS_DIR / f"{year}_경희대논술_채점기준과_해설.md"
        if not path.exists():
            print(f"  [skip] 경희대 {year}: 파일 없음")
            continue
        text = path.read_text(encoding="utf-8")
        sections = [
            ("채점척도해설", extract_section(text, "## 4. 채점 척도", ["## 5. 모범 답안"])),
            ("문제해설", extract_section(text, "## 6. 문제 해설", [])),
        ]
        for doc_type, body in sections:
            if not body:
                continue
            for i, chunk in enumerate(chunk_text(body, max_chars=900)):
                records.append(
                    ChunkRecord(
                        id_key=f"kyunghee::{year}::{doc_type}::{i}",
                        text=chunk,
                        metadata={
                            "source": "경희대",
                            "university": "경희대",
                            "year": year,
                            "doc_type": doc_type,
                            "file": path.name,
                        },
                    )
                )
        print(f"  [ok] 경희대 {year} 채점척도해설/문제해설")
    return records


# ---------------------------------------------------------------------------
# 한양대: 평가기준.md의 "출제 의도 및 문제 해설"
# ---------------------------------------------------------------------------


def load_hanyang_chunks() -> list[ChunkRecord]:
    records: list[ChunkRecord] = []
    for year in (2025, 2026):
        path = DOCS_DIR / f"한양대 상경 {year} 평가기준.md"
        if not path.exists():
            print(f"  [skip] 한양대 {year}: 파일 없음")
            continue
        text = path.read_text(encoding="utf-8")
        body = extract_section(text, "1. 출제 의도 및 문제 해설", ["2. 분석적 평가의 영역"])
        if not body:
            continue
        for i, chunk in enumerate(chunk_text(body, max_chars=900)):
            records.append(
                ChunkRecord(
                    id_key=f"hanyang::{year}::출제의도해설::{i}",
                    text=chunk,
                    metadata={
                        "source": "한양대",
                        "university": "한양대",
                        "year": year,
                        "doc_type": "출제의도해설",
                        "file": path.name,
                    },
                )
            )
        print(f"  [ok] 한양대 {year} 출제의도해설")
    return records


def run() -> None:
    records = load_gukrip_chunks() + load_kyunghee_chunks() + load_hanyang_chunks()

    ids = [hashlib.sha1(r.id_key.encode("utf-8")).hexdigest() for r in records]
    texts = [r.text for r in records]
    metadatas = [{**r.metadata, "chunk_key": r.id_key} for r in records]

    vector_store.reset_collection()
    vector_store.upsert_chunks(ids, texts, metadatas)

    print(f"\n완료: {len(records)}개 청크 색인 (컬렉션: {vector_store.COLLECTION_NAME})")


if __name__ == "__main__":
    run()
