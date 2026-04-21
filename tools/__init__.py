from __future__ import annotations

import json
import re
from typing import Any


def parse_json(text: str) -> Any:
    text = (text or "").strip()
    if text.startswith("```") and text.endswith("```"):
        lines = text.splitlines()
        if len(lines) >= 2:
            text = "\n".join(lines[1:-1]).strip()

    try:
        return json.loads(text)
    except Exception:
        pass

    for pattern in (r"(\{.*\})", r"(\[.*\])"):
        m = re.search(pattern, text, flags=re.DOTALL)
        if not m:
            continue
        try:
            return json.loads(m.group(1))
        except Exception:
            continue
    raise ValueError("Failed to parse JSON payload")


__all__ = ["parse_json"]
