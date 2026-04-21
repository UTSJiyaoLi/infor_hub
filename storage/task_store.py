from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

from schemas.api import TaskStatus
from settings import settings
from storage.workspace_store import utc_now


@dataclass
class TaskRecord:
    task_id: str
    status: TaskStatus
    created_at: str
    updated_at: str
    message: str
    artifact_paths: Dict[str, str]
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "status": self.status.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "message": self.message,
            "artifact_paths": self.artifact_paths,
            "result": self.result,
            "error": self.error,
        }


class TaskStore:
    def __init__(self, root: Path | None = None):
        self.root = root or settings.task_dir
        self.root.mkdir(parents=True, exist_ok=True)

    def _task_path(self, task_id: str) -> Path:
        return self.root / f"{task_id}.json"

    def create(self, task_id: str, artifact_paths: Dict[str, str]) -> TaskRecord:
        now = utc_now()
        rec = TaskRecord(
            task_id=task_id,
            status=TaskStatus.pending,
            created_at=now,
            updated_at=now,
            message="Task created",
            artifact_paths=artifact_paths,
        )
        self.save(rec)
        return rec

    def save(self, rec: TaskRecord) -> None:
        self._task_path(rec.task_id).write_text(json.dumps(rec.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")

    def get(self, task_id: str) -> Optional[TaskRecord]:
        path = self._task_path(task_id)
        if not path.exists():
            return None
        payload = json.loads(path.read_text(encoding="utf-8"))
        return TaskRecord(
            task_id=payload["task_id"],
            status=TaskStatus(payload["status"]),
            created_at=payload["created_at"],
            updated_at=payload["updated_at"],
            message=payload.get("message", ""),
            artifact_paths=payload.get("artifact_paths", {}),
            result=payload.get("result"),
            error=payload.get("error"),
        )

    def mark_running(self, task_id: str, message: str = "Task running") -> None:
        rec = self.get(task_id)
        if not rec:
            return
        rec.status = TaskStatus.running
        rec.message = message
        rec.updated_at = utc_now()
        self.save(rec)

    def mark_success(self, task_id: str, result: Dict[str, Any], message: str = "Task completed") -> None:
        rec = self.get(task_id)
        if not rec:
            return
        rec.status = TaskStatus.success
        rec.message = message
        rec.result = result
        rec.updated_at = utc_now()
        self.save(rec)

    def mark_failed(self, task_id: str, error: str, message: str = "Task failed") -> None:
        rec = self.get(task_id)
        if not rec:
            return
        rec.status = TaskStatus.failed
        rec.message = message
        rec.error = error
        rec.updated_at = utc_now()
        self.save(rec)


TASK_STORE = TaskStore()

