from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import streamlit as st

from graph import run_collector


DEFAULT_SOURCES_PATH = "data/raw_sources_tavily.json"


def _load_sources(path: str) -> List[Dict[str, Any]]:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Source file not found: {p}")

    if p.suffix.lower() == ".jsonl":
        rows: List[Dict[str, Any]] = []
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
        return rows

    return json.loads(p.read_text(encoding="utf-8"))


def _save_outputs(result: Dict[str, Any], topic: str) -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    topic_safe = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in topic)[:80] or "topic"
    out_dir = Path("outputs") / f"{topic_safe}_{ts}"
    out_dir.mkdir(parents=True, exist_ok=True)

    (out_dir / "result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    (out_dir / "final_report.md").write_text(result.get("final_report", ""), encoding="utf-8")
    (out_dir / "case_table.md").write_text(result.get("case_table", ""), encoding="utf-8")
    (out_dir / "logs.txt").write_text("\n".join(result.get("logs", [])), encoding="utf-8")
    return out_dir


st.set_page_config(page_title="Infor Hub Generative UI", layout="wide")
st.title("Infor Hub Generative UI")
st.caption("本地前端运行，抓取数据后调用 LangGraph 工作流生成报告。")

with st.sidebar:
    st.subheader("LLM Endpoint")
    st.caption("推荐通过 SSH 端口转发把服务器容器 LLM 暴露到本地。")
    model_name = st.text_input("COLLECTOR_MODEL", value=os.environ.get("COLLECTOR_MODEL", "openai:gpt-4o"))
    openai_base_url = st.text_input("OPENAI_BASE_URL", value=os.environ.get("OPENAI_BASE_URL", ""))
    openai_api_key = st.text_input("OPENAI_API_KEY", value=os.environ.get("OPENAI_API_KEY", ""), type="password")

    if st.button("Apply Env"):
        os.environ["COLLECTOR_MODEL"] = model_name.strip()
        if openai_base_url.strip():
            os.environ["OPENAI_BASE_URL"] = openai_base_url.strip()
        if openai_api_key.strip():
            os.environ["OPENAI_API_KEY"] = openai_api_key.strip()
        st.success("Environment variables applied for this UI process.")

st.subheader("Run Collector")
topic = st.text_input("Topic", value="floating offshore wind demonstration projects")
user_goal = st.text_area(
    "User Goal",
    value="生成工程情报简报，包含案例对比、趋势分析、风险与建议。",
    height=100,
)
sources_path = st.text_input("Raw Sources Path (.json or .jsonl)", value=DEFAULT_SOURCES_PATH)

col1, col2 = st.columns([1, 1])
with col1:
    preview = st.button("Preview Sources")
with col2:
    run = st.button("Run Workflow", type="primary")

if preview:
    try:
        rows = _load_sources(sources_path)
        st.success(f"Loaded {len(rows)} source records.")
        st.json(rows[:2])
    except Exception as exc:
        st.error(str(exc))

if run:
    try:
        rows = _load_sources(sources_path)
        st.info(f"Loaded {len(rows)} sources. Running workflow...")
        result = run_collector(
            {
                "topic": topic.strip(),
                "user_goal": user_goal.strip(),
                "raw_sources": rows,
            }
        )

        out_dir = _save_outputs(result, topic=topic)
        st.success(f"Workflow complete. Outputs saved to: {out_dir}")

        st.markdown("### Final Report")
        st.markdown(result.get("final_report", ""))

        st.markdown("### Case Table")
        st.markdown(result.get("case_table", ""))

        with st.expander("Logs", expanded=False):
            for line in result.get("logs", []):
                st.text(line)
    except Exception as exc:
        st.exception(exc)
