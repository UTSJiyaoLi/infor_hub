from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict


def _parse_env_file(path: Path) -> Dict[str, str]:
    values: Dict[str, str] = {}
    if not path.exists():
        return values
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        values[key.strip()] = val.strip().strip("'").strip('"')
    return values


def _load_env_chain() -> None:
    root = Path(__file__).resolve().parent
    env_example = root / ".env.example"
    env_local = root / ".env.local"
    for src in (env_example, env_local):
        for key, val in _parse_env_file(src).items():
            os.environ.setdefault(key, val)


@dataclass(frozen=True)
class Settings:
    app_name: str
    app_env: str
    collector_model: str
    workspace_root: Path
    output_root: Path
    log_dir: Path
    task_dir: Path
    source_registry_path: Path
    default_time_window_days: int
    max_sources_per_task: int


def load_settings() -> Settings:
    _load_env_chain()
    root = Path(__file__).resolve().parent
    output_root = Path(os.getenv("INFOR_OUTPUT_DIR", str(root / "outputs")))
    log_dir = Path(os.getenv("INFOR_LOG_DIR", str(root / ".logs")))
    task_dir = Path(os.getenv("INFOR_TASK_DIR", str(output_root / "tasks")))
    workspace_root = Path(os.getenv("COLLECTOR_WORKSPACE", str(root / ".collector_workspace")))
    source_registry_path = Path(
        os.getenv("INFOR_SOURCE_REGISTRY", str(root / "configs" / "source_registry.json"))
    )

    for p in (output_root, log_dir, task_dir, workspace_root, source_registry_path.parent):
        p.mkdir(parents=True, exist_ok=True)

    return Settings(
        app_name=os.getenv("INFOR_APP_NAME", "Infor Hub API"),
        app_env=os.getenv("INFOR_APP_ENV", "local"),
        collector_model=os.getenv("COLLECTOR_MODEL", "openai:gpt-4o"),
        workspace_root=workspace_root,
        output_root=output_root,
        log_dir=log_dir,
        task_dir=task_dir,
        source_registry_path=source_registry_path,
        default_time_window_days=int(os.getenv("INFOR_TIME_WINDOW_DAYS", "90")),
        max_sources_per_task=int(os.getenv("INFOR_MAX_SOURCES_PER_TASK", "100")),
    )


settings = load_settings()

