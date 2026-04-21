from __future__ import annotations

from typing import Any, Dict

from services.pipeline_v2 import run_intelligence_pipeline


def run_collector(inputs: Dict[str, Any]) -> Dict[str, Any]:
    topic = str(inputs.get("topic") or "").strip()
    if not topic:
        raise ValueError("topic is required")
    user_goal = str(inputs.get("user_goal") or "")
    raw_sources = inputs.get("raw_sources") or []
    if not isinstance(raw_sources, list):
        raise ValueError("raw_sources must be a list")
    return run_intelligence_pipeline(topic=topic, user_goal=user_goal, raw_sources=raw_sources).to_dict()


# Backward-compatible export name.
graph = None

__all__ = ["run_collector", "graph"]
