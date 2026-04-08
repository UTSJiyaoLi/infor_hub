import os
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import requests
from bs4 import BeautifulSoup
from deepagents import create_deep_agent
from langchain.chat_models import init_chat_model
from langchain_core.tools import tool
from tavily import TavilyClient


WORKSPACE_ROOT = os.environ.get("COLLECTOR_WORKSPACE", ".collector_workspace")
DEFAULT_MAX_RESULTS = int(os.environ.get("COLLECTOR_MAX_RESULTS", "5"))
DEFAULT_MODEL = os.environ.get("COLLECTOR_MODEL", "openai:gpt-4o")

os.makedirs(WORKSPACE_ROOT, exist_ok=True)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _task_dir(task_id: str) -> str:
    path = os.path.join(WORKSPACE_ROOT, task_id)
    os.makedirs(path, exist_ok=True)
    return path


def _append_jsonl(path: str, row: Dict[str, Any]) -> None:
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _safe_filename(value: str) -> str:
    keep = []
    for ch in value:
        if ch.isalnum() or ch in {"-", "_"}:
            keep.append(ch)
        else:
            keep.append("_")
    return "".join(keep).strip("_")[:80] or "task"


@tool
def create_collection_task(topic: str, goal: str, scope: Optional[List[str]] = None) -> Dict[str, Any]:
    """Create a new collection task and initialize workspace files."""
    task_id = f"{_safe_filename(topic)}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    task_path = _task_dir(task_id)
    payload = {
        "task_id": task_id,
        "topic": topic,
        "goal": goal,
        "scope": scope or [],
        "created_at": _utc_now(),
        "status": "created",
    }
    with open(os.path.join(task_path, "task.json"), "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    for filename, initial in {
        "raw_sources.jsonl": "",
        "facts.jsonl": "",
        "notes.md": f"# Notes\n\n## Topic\n{topic}\n\n## Goal\n{goal}\n",
        "timeline.md": "# Timeline\n\n",
        "gaps.md": "# Gaps\n\n",
        "report.md": "# Report\n\n",
    }.items():
        with open(os.path.join(task_path, filename), "w", encoding="utf-8") as f:
            f.write(initial)

    return payload


@tool
def search_sources(query: str, max_results: int = DEFAULT_MAX_RESULTS, topic: str = "general") -> Dict[str, Any]:
    """Search the web for candidate sources for a collection task."""
    api_key = os.environ.get("TAVILY_API_KEY")
    if not api_key:
        raise ValueError("TAVILY_API_KEY is required for search_sources")

    client = TavilyClient(api_key=api_key)
    result = client.search(query=query, max_results=max_results, topic=topic)
    return result


@tool
def collect_webpage(task_id: str, url: str, source_type: str = "web") -> Dict[str, Any]:
    """Fetch a webpage, extract readable text, and store a structured source record."""
    headers = {
        "User-Agent": "collector-agent/0.1 (+https://example.local)"
    }
    response = requests.get(url, headers=headers, timeout=20)
    response.raise_for_status()

    content_type = response.headers.get("content-type", "")
    if "text/html" not in content_type:
        text = response.text[:12000]
        title = url
    else:
        soup = BeautifulSoup(response.text, "html.parser")
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        title = (soup.title.string or url).strip() if soup.title else url
        text = "\n".join(
            line.strip() for line in soup.get_text("\n").splitlines() if line.strip()
        )[:20000]

    record = {
        "id": f"src_{datetime.now().strftime('%Y%m%d%H%M%S%f')}",
        "url": url,
        "title": title,
        "source_type": source_type,
        "collected_at": _utc_now(),
        "summary": text[:1500],
        "tags": [],
        "confidence": "medium",
    }
    task_path = _task_dir(task_id)
    _append_jsonl(os.path.join(task_path, "raw_sources.jsonl"), record)
    return record


@tool
def save_fact(
    task_id: str,
    statement: str,
    category: str,
    source_ids: List[str],
    confidence: str = "medium",
    status: str = "tentative",
) -> Dict[str, Any]:
    """Save a normalized fact extracted from one or more sources."""
    record = {
        "fact_id": f"fact_{datetime.now().strftime('%Y%m%d%H%M%S%f')}",
        "statement": statement,
        "category": category,
        "source_ids": source_ids,
        "confidence": confidence,
        "status": status,
        "saved_at": _utc_now(),
    }
    task_path = _task_dir(task_id)
    _append_jsonl(os.path.join(task_path, "facts.jsonl"), record)
    return record


@tool
def update_markdown_file(task_id: str, filename: str, content: str, mode: str = "append") -> str:
    """Write or append markdown content to notes/report/timeline/gaps files inside a task workspace."""
    allowed = {"notes.md", "timeline.md", "gaps.md", "report.md"}
    if filename not in allowed:
        raise ValueError(f"filename must be one of {sorted(allowed)}")

    task_path = _task_dir(task_id)
    path = os.path.join(task_path, filename)
    if mode == "overwrite":
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
    else:
        with open(path, "a", encoding="utf-8") as f:
            f.write(content)
            if not content.endswith("\n"):
                f.write("\n")
    return path


@tool
def read_task_file(task_id: str, filename: str) -> str:
    """Read a file from the task workspace."""
    task_path = _task_dir(task_id)
    path = os.path.join(task_path, filename)
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


COLLECTOR_SYSTEM_PROMPT = """
You are an information collection agent specialized in building reusable research packages.

Your job is to collect, organize, verify, and summarize information about a target topic.

Workflow:
1. Create a collection task first.
2. Make a concise research plan with TODOs.
3. Search for sources in batches by subtopic.
4. Collect important webpages into the workspace.
5. Extract normalized facts from collected sources.
6. Build notes, a timeline, open questions, and a final report.

Rules:
- Prefer primary and official sources first.
- Separate facts from interpretation.
- Save major findings as structured facts.
- Record uncertainty explicitly.
- Deduplicate repeated claims.
- Do not write the final report until at least several sources have been collected.
- The report should include: overview, key findings, timeline, risks/unknowns, and source-backed conclusions.

When collecting on a software repository or product, focus on:
- architecture
- examples and reusable patterns
- implementation choices
- parts suitable for adaptation into an information collector
- limitations and integration constraints
""".strip()


model = init_chat_model(DEFAULT_MODEL)

agent = create_deep_agent(
    model=model,
    tools=[
        create_collection_task,
        search_sources,
        collect_webpage,
        save_fact,
        update_markdown_file,
        read_task_file,
    ],
    system_prompt=COLLECTOR_SYSTEM_PROMPT,
)


if __name__ == "__main__":
    user_request = {
        "messages": [
            {
                "role": "user",
                "content": (
                    "Create a collection package about langchain-ai/deepagents, "
                    "focusing on patterns we can reuse for an information collector."
                ),
            }
        ]
    }
    result = agent.invoke(user_request)
    print(result)
