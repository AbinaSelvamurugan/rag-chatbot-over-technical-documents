from __future__ import annotations
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
import re
from bs4 import BeautifulSoup
from pypdf import PdfReader

EXTENSIONS = {'.pdf', '.html', '.htm', '.md', '.txt'}

class ExtractionError(ValueError):
    pass

@dataclass(frozen=True)
class Segment:
    text: str
    page_number: int | None = None


def extract(name: str, data: bytes) -> list[Segment]:
    suffix = Path(name).suffix.lower()
    if suffix not in EXTENSIONS:
        raise ExtractionError(f'Unsupported extension: {suffix}')
    if not data:
        raise ExtractionError('Empty file')
    if suffix == '.pdf':
        if not data.startswith(b'%PDF-'):
            raise ExtractionError('PDF signature missing')
        try:
            pdf = PdfReader(BytesIO(data), strict=False)
            segments = [Segment(page.extract_text(extraction_mode='layout') or '', i+1) for i, page in enumerate(pdf.pages)]
        except Exception as exc:
            raise ExtractionError('Corrupted or unreadable PDF') from exc
        if not any(s.text.strip() for s in segments):
            raise ExtractionError('PDF has no extractable text; optional OCR is required')
        return [s for s in segments if s.text.strip()]
    try:
        text = data.decode('utf-8-sig')
    except UnicodeDecodeError as exc:
        raise ExtractionError('Text must be UTF-8') from exc
    if '\x00' in text:
        raise ExtractionError('Binary content found in text file')
    if suffix in {'.html', '.htm'}:
        soup = BeautifulSoup(text, 'html.parser')
        if soup.find('html') is None and soup.find('body') is None:
            raise ExtractionError('Malformed HTML: missing document root')
        for x in soup.select('script,style,nav,footer,header,form,iframe'):
            x.decompose()
        for tag in soup.select('h1,h2,h3,h4,h5,h6'):
            tag.insert_before('\n' + '#' * int(tag.name[1]) + ' ')
            tag.insert_after('\n')
        for tag in soup.select('pre,code'):
            tag.insert_before('\n```\n')
            tag.insert_after('\n```\n')
        for tag in soup.select('tr'):
            tag.insert_after('\n')
        for tag in soup.select('td,th'):
            tag.insert_after(' | ')
        text = (soup.select_one('main') or soup.select_one('article') or soup.body or soup).get_text(separator=' ', strip=False)
    text = re.sub(r'\r\n?', '\n', text)
    text = re.sub(r'(?m)^\s*\n{3,}', '\n\n', text)
    if not text.strip():
        raise ExtractionError('Document contains no usable text')
    return [Segment(text.strip())]
