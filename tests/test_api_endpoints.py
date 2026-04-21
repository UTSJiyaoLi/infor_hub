from __future__ import annotations

import json
import time

from fastapi.testclient import TestClient

from api.app import app


def _payload():
    return {
        "topic": "offshore hydrogen platform",
        "user_goal": "test report",
        "raw_sources": [
            {
                "title": "Demo",
                "source_type": "report",
                "url": "https://example.com",
                "text": "Floating hydrogen prototype demonstration with DNV certification and funding support.",
            }
        ],
    }


def test_health():
    client = TestClient(app)
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_task_lifecycle():
    client = TestClient(app)
    create = client.post("/tasks", json=_payload())
    assert create.status_code == 200
    body = create.json()
    task_id = body["task_id"]
    assert body["status"] in {"pending", "running"}

    final = None
    for _ in range(40):
        r = client.get(f"/tasks/{task_id}")
        assert r.status_code == 200
        final = r.json()
        if final["status"] in {"success", "failed"}:
            break
        time.sleep(0.1)

    assert final is not None
    assert final["status"] == "success"
    assert "final_report_md" in final["artifact_paths"]


def test_report_stream_sse():
    client = TestClient(app)
    with client.stream("POST", "/report/stream", json=_payload()) as resp:
        assert resp.status_code == 200
        chunks = []
        for text in resp.iter_text():
            if text:
                chunks.append(text)
            if "event: done" in "".join(chunks):
                break
    joined = "".join(chunks)
    assert "event: step" in joined
    assert "event: done" in joined


def test_collect_sync():
    client = TestClient(app)
    r = client.post("/collect", json=_payload())
    assert r.status_code == 200
    data = r.json()
    assert "final_report" in data
    assert isinstance(data["candidates"], list)

