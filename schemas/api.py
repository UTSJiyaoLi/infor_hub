from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    pending = "pending"
    running = "running"
    success = "success"
    failed = "failed"


class CreateTaskRequest(BaseModel):
    topic: str = Field(..., min_length=2)
    user_goal: str = Field(default="")
    raw_sources: List[Dict[str, Any]] = Field(default_factory=list)
    time_window_days: Optional[int] = None
    source_ids: List[str] = Field(default_factory=list)


class CreateTaskResponse(BaseModel):
    task_id: str
    status: TaskStatus
    task_path: str


class TaskStateResponse(BaseModel):
    task_id: str
    status: TaskStatus
    created_at: str
    updated_at: str
    message: str
    artifact_paths: Dict[str, str] = Field(default_factory=dict)
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class ReportStreamRequest(BaseModel):
    topic: str = Field(..., min_length=2)
    user_goal: str = Field(default="")
    raw_sources: List[Dict[str, Any]] = Field(default_factory=list)
    time_window_days: Optional[int] = None
    source_ids: List[str] = Field(default_factory=list)

