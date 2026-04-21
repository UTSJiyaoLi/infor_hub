from __future__ import annotations

import json
from pathlib import Path
from typing import List

from schemas.pipeline import SourceSpec
from settings import settings


def load_source_registry(path: Path | None = None) -> List[SourceSpec]:
    registry_path = path or settings.source_registry_path
    if not registry_path.exists():
        return []
    payload = json.loads(registry_path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        return []
    items: List[SourceSpec] = []
    for row in payload:
        try:
            item = SourceSpec.model_validate(row)
        except Exception:
            continue
        if item.enabled:
            items.append(item)
    return items

