from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256
import re
from .extraction import Segment

@dataclass(frozen=True)
class Chunk:
    id: str
    text: str
    section: str | None
    page: int | None


def chunk_segments(document_id: str, segments: list[Segment], size: int = 1100, overlap: int = 150) -> list[Chunk]:
    if size <= 0 or overlap < 0 or overlap >= size:
        raise ValueError('Require 0 <= overlap < size')
    result: list[Chunk] = []
    seen: set[tuple[int | None, str]] = set()
    for segment in segments:
        # Keep code blocks and paragraph breaks; split oversized paragraphs safely at token boundaries.
        section: str | None = None
        blocks = re.split(r'(?=^#{1,6} +[^\n]+$)', segment.text, flags=re.M)
        for block in blocks:
            if not block.strip():
                continue
            match = re.match(r'^(#{1,6})\s+([^\n]+)', block.strip())
            if match:
                section = match.group(2).strip()
            heading = ('# ' + section + '\n') if section else ''
            payload = block.strip()
            if len(payload) <= size:
                pieces = [payload]
            else:
                # LangChain's recursive splitter preserves line boundaries/technical symbols.
                try:
                    from langchain_text_splitters import RecursiveCharacterTextSplitter
                except ImportError:
                    pieces = _offline_split(payload, size - len(heading), overlap)
                else:
                    splitter = RecursiveCharacterTextSplitter(chunk_size=max(100, size-len(heading)), chunk_overlap=overlap,
                        separators=['\n```', '\n\n', '\n', ' ', ''], keep_separator=True)
                    pieces = splitter.split_text(payload)
            for piece in pieces:
                text = (heading + piece if heading and not piece.startswith('#') else piece).strip()
                if not text or (segment.page_number, text) in seen:
                    continue
                seen.add((segment.page_number, text))
                checksum = sha256(f'{document_id}\0{segment.page_number}\0{text}'.encode()).hexdigest()[:24]
                result.append(Chunk(checksum, text, section, segment.page_number))
    return result


def _offline_split(text: str, size: int, overlap: int) -> list[str]:
    if size <= overlap or size <= 0:
        raise ValueError('Invalid splitter limits')
    result = []
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        if end < len(text):
            break_at = max(text.rfind('\n', start + size//2, end), text.rfind(' ', start + size//2, end))
            if break_at > start:
                end = break_at + 1
        result.append(text[start:end].strip())
        if end == len(text):
            break
        start = max(start+1, end-overlap)
    return result
