from __future__ import annotations

from hashlib import md5
from typing import Any, Dict, List

from schemas.pipeline import NormalizedDocument


def _guess_lang(text: str) -> str:
    if any("\u4e00" <= ch <= "\u9fff" for ch in text[:500]):
        return "zh"
    return "en"


def normalize_documents(raw_sources: List[Dict[str, Any]]) -> List[NormalizedDocument]:
    docs: List[NormalizedDocument] = []
    for row in raw_sources:
        title = str(row.get("title") or "Untitled").strip()
        body = str(row.get("text") or "").strip()
        if not body:
            continue
        source_type = str(row.get("source_type") or "web")
        url = str(row.get("url") or "")
        source = str(row.get("source_id") or row.get("domain") or source_type)
        doc_id = md5(f"{title}|{url}|{body[:200]}".encode("utf-8")).hexdigest()[:16]
        docs.append(
            NormalizedDocument(
                doc_id=doc_id,
                title=title,
                published_at=row.get("published_at"),
                source=source,
                url=url,
                body_markdown=body,
                summary=body[:300],
                language=_guess_lang(body),
                doc_type=source_type,
                metadata={
                    "domain": row.get("domain"),
                    "source_type": source_type,
                },
            )
        )
    return docs

