from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4
from typing import Any, Dict

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from schemas.api import (
    CreateTaskRequest,
    CreateTaskResponse,
    ReportStreamRequest,
    TaskStateResponse,
)
from services.pipeline_v2 import run_intelligence_pipeline, stream_report_events
from settings import settings
from storage.task_store import TASK_STORE
from storage.workspace_store import utc_now


def _build_artifact_paths(task_id: str) -> Dict[str, str]:
    base = settings.output_root / task_id
    base.mkdir(parents=True, exist_ok=True)
    return {
        "base_dir": str(base),
        "result_json": str(base / "result.json"),
        "final_report_md": str(base / "final_report.md"),
    }


def _write_task_artifacts(task_id: str, result: Dict[str, Any]) -> None:
    paths = _build_artifact_paths(task_id)
    Path(paths["result_json"]).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    Path(paths["final_report_md"]).write_text(str(result.get("final_report", "")), encoding="utf-8")


def _run_task(task_id: str, payload: CreateTaskRequest) -> None:
    TASK_STORE.mark_running(task_id)
    try:
        result = run_intelligence_pipeline(
            topic=payload.topic,
            user_goal=payload.user_goal,
            raw_sources=payload.raw_sources,
        ).to_dict()
        _write_task_artifacts(task_id, result)
        TASK_STORE.mark_success(task_id, result=result, message="Task completed and artifacts saved")
    except Exception as exc:
        TASK_STORE.mark_failed(task_id, error=str(exc))


def create_app():
    app = FastAPI(title=settings.app_name, version="0.2.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://127.0.0.1:3000",
            "http://localhost:3000",
            "http://127.0.0.1:3001",
            "http://localhost:3001",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def health() -> Dict[str, Any]:
        return {"status": "ok", "env": settings.app_env, "time": utc_now()}

    @app.post("/tasks", response_model=CreateTaskResponse)
    def create_task(req: CreateTaskRequest, background_tasks: BackgroundTasks) -> CreateTaskResponse:
        task_id = uuid4().hex
        paths = _build_artifact_paths(task_id)
        rec = TASK_STORE.create(task_id=task_id, artifact_paths=paths)
        background_tasks.add_task(_run_task, task_id, req)
        return CreateTaskResponse(task_id=task_id, status=rec.status, task_path=paths["base_dir"])

    @app.get("/tasks/{task_id}", response_model=TaskStateResponse)
    def get_task(task_id: str) -> TaskStateResponse:
        rec = TASK_STORE.get(task_id)
        if rec is None:
            raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")
        return TaskStateResponse(
            task_id=rec.task_id,
            status=rec.status,
            created_at=rec.created_at,
            updated_at=rec.updated_at,
            message=rec.message,
            artifact_paths=rec.artifact_paths,
            result=rec.result,
            error=rec.error,
        )

    @app.post("/report/stream")
    def report_stream(req: ReportStreamRequest):
        def _event_stream():
            try:
                gen = stream_report_events(req.topic, req.user_goal, req.raw_sources)
                while True:
                    event = next(gen)
                    yield f"event: step\ndata: {json.dumps(event, ensure_ascii=False)}\n\n"
            except StopIteration as stop:
                result = stop.value.to_dict() if stop.value else {}
                yield f"event: done\ndata: {json.dumps(result, ensure_ascii=False)}\n\n"
            except Exception as exc:
                err = {"error": str(exc)}
                yield f"event: error\ndata: {json.dumps(err, ensure_ascii=False)}\n\n"

        return StreamingResponse(_event_stream(), media_type="text/event-stream")

    @app.post("/collect")
    def collect(req: ReportStreamRequest) -> Dict[str, Any]:
        return run_intelligence_pipeline(
            topic=req.topic,
            user_goal=req.user_goal,
            raw_sources=req.raw_sources,
        ).to_dict()

    return app


app = create_app()
