from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict


WORKSPACE_ROOT = Path(os.environ.get("COLLECTOR_WORKSPACE", ".collector_workspace"))
WORKSPACE_ROOT.mkdir(parents=True, exist_ok=True)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_task_dir(task_id: str) -> Path:
    path = WORKSPACE_ROOT / task_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def append_jsonl(path: Path, row: Dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")

