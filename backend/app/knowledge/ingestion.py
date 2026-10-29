"""Adapted from customer-service foundation/knowledge.py (Apache-2.0)."""
from app.core.exceptions import AppError
from .schemas import ChunkSettings

def split_text(content: str, settings: ChunkSettings) -> list[str]:
    rows = []
    for part in content.split(settings.separator.replace('\\n', '\n')):
        start = 0
        while start < len(part):
            end = min(start + settings.target_chars, len(part))
            segment = part[start:end].strip()
            if segment: rows.append(segment)
            if len(rows) > 500: raise AppError('切片超过500条，请拆分文档或增大长度', code='TOO_MANY_CHUNKS', status_code=422)
            if end == len(part): break
            start = end - settings.overlap_chars
    if not rows: raise AppError('知识正文不能为空', code='EMPTY_KNOWLEDGE', status_code=422)
    return rows
