"""`논술문서 텍스트/` 원본 파일 파싱 공통 유틸.

`scripts/seed_from_repo.py`(1단계, 구조화 데이터 → SQLite)와
`scripts/build_vector_index.py`(3단계, 비정형 텍스트 → 벡터DB)가 함께 쓴다.
"""

from __future__ import annotations


def extract_section(text: str, start_heading: str, end_headings: list[str]) -> str:
    """start_heading 다음부터, end_headings 중 가장 먼저 나오는 지점(또는 끝)까지 잘라 반환."""
    start = text.find(start_heading)
    if start == -1:
        return ""
    start += len(start_heading)
    end = len(text)
    for h in end_headings:
        idx = text.find(h, start)
        if idx != -1:
            end = min(end, idx)
    return text[start:end].strip()


def chunk_text(text: str, max_chars: int = 900, overlap_chars: int = 100) -> list[str]:
    """문단(빈 줄) 경계를 존중하면서 max_chars 근처로 텍스트를 나눈다.

    - 문단 하나가 max_chars보다 길면 어쩔 수 없이 그 문단만으로 청크를 만든다(강제로 자르지 않음 —
      의미 단위가 깨지는 것을 피함. 채점 사례처럼 긴 문단이 있어도 검색 근거로는 문단 전체가 유용함).
    - overlap_chars만큼 이전 청크의 꼬리를 다음 청크 앞에 덧붙여 문맥 단절을 줄인다.
    """
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if not paragraphs:
        return []

    chunks: list[str] = []
    current = ""
    for para in paragraphs:
        candidate = f"{current}\n\n{para}" if current else para
        if len(candidate) <= max_chars or not current:
            current = candidate
        else:
            chunks.append(current)
            tail = current[-overlap_chars:] if overlap_chars else ""
            current = f"{tail}\n\n{para}" if tail else para
    if current:
        chunks.append(current)
    return chunks
