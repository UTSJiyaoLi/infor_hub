from __future__ import annotations

import os
from typing import Any, Dict

from langchain.chat_models import init_chat_model

from workflows.research_flow import build_research_graph


# ============================================================
# Model factory
# ============================================================

DEFAULT_MODEL = os.environ.get("COLLECTOR_MODEL", "openai:gpt-4o")


def get_default_model():
    """
    Initialize the default chat model for the collector system.

    You can override the model with:
        export COLLECTOR_MODEL="openai:gpt-4o"
        export COLLECTOR_MODEL="openai:gpt-4.1"
        export COLLECTOR_MODEL="anthropic:claude-3-7-sonnet-latest"

    The exact supported values depend on your LangChain setup.
    """
    return init_chat_model(DEFAULT_MODEL)


# ============================================================
# Graph instance
# ============================================================

collector_graph = build_research_graph()


# ============================================================
# Public wrapper
# ============================================================

def run_collector(inputs: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute the collector workflow with injected model.

    Expected inputs usually include:
    - topic
    - user_goal
    - raw_sources

    Example:
        result = run_collector({
            "topic": "波浪能发电技术",
            "user_goal": "产出类似工程科技动态的情报简报",
            "raw_sources": [...]
        })
    """
    state = dict(inputs)

    if "model" not in state or state["model"] is None:
        state["model"] = get_default_model()

    return collector_graph.invoke(state)


# ============================================================
# LangGraph export
# ============================================================

graph = collector_graph