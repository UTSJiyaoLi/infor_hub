from __future__ import annotations

from typing import Any, Dict, List

import requests

from schemas.pipeline import SourceSpec


def collect_raw_items(
    *,
    topic: str,
    raw_sources: List[Dict[str, Any]],
    registry_items: List[SourceSpec],
    max_sources: int,
) -> List[Dict[str, Any]]:
    rows = list(raw_sources or [])
    if rows:
        return rows[:max_sources]
    if len(rows) >= max_sources:
        return rows[:max_sources]

    for src in registry_items:
        if len(rows) >= max_sources:
            break
        for entry in src.entry_urls:
            if len(rows) >= max_sources:
                break
            try:
                resp = requests.get(entry, timeout=12, headers={"User-Agent": "infor-hub-collector/0.1"})
                resp.raise_for_status()
                text = resp.text[:20000]
            except Exception:
                continue
            rows.append(
                {
                    "title": f"{src.name} {topic}",
                    "source_type": src.source_type,
                    "url": entry,
                    "text": text,
                    "source_id": src.source_id,
                    "domain": src.domain,
                }
            )
    return rows[:max_sources]
