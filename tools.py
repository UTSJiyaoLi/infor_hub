from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional, Type, TypeVar

from pydantic import BaseModel, ValidationError
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.language_models.chat_models import BaseChatModel

from prompts import (
    TOPIC_DECOMPOSITION_PROMPT,
    SOURCE_COLLECTION_PROMPT,
    SOURCE_SUMMARY_PROMPT,
    TECH_PROFILE_EXTRACTION_PROMPT,
    CASE_COMPARISON_PROMPT,
    TREND_ANALYSIS_PROMPT,
    EDITORIAL_NOTE_PROMPT,
    FINAL_REPORT_PROMPT,
    CASE_TABLE_PROMPT,
    GAP_ANALYSIS_PROMPT,
)
from schemas.technology import (
    TechnologyProfile,
    ComparisonResult,
    TrendAnalysis,
    IntelligenceGap,
    SourceReference,
)

T = TypeVar("T", bound=BaseModel)


# ============================================================
# 基础工具：文本与 JSON 解析
# ============================================================

def strip_code_fence(text: str) -> str:
    """
    Remove surrounding markdown code fences if present.
    """
    text = text.strip()

    if text.startswith("```") and text.endswith("```"):
        lines = text.splitlines()
        if len(lines) >= 2:
            return "\n".join(lines[1:-1]).strip()

    return text


def try_extract_json_block(text: str) -> str:
    """
    Try to extract the first JSON object or array from a model response.

    This is a defensive parser for LLM outputs that may include prose
    before or after JSON.
    """
    text = strip_code_fence(text)

    # 尝试直接作为 JSON 解析
    try:
        json.loads(text)
        return text
    except Exception:
        pass

    # 找第一个 { ... } 或 [ ... ]
    obj_match = re.search(r"(\{.*\})", text, flags=re.DOTALL)
    if obj_match:
        candidate = obj_match.group(1).strip()
        try:
            json.loads(candidate)
            return candidate
        except Exception:
            pass

    arr_match = re.search(r"(\[.*\])", text, flags=re.DOTALL)
    if arr_match:
        candidate = arr_match.group(1).strip()
        try:
            json.loads(candidate)
            return candidate
        except Exception:
            pass

    raise ValueError("Failed to extract valid JSON from model output.")


def parse_json(text: str) -> Any:
    """
    Parse JSON from possibly messy model output.
    """
    payload = try_extract_json_block(text)
    return json.loads(payload)


def safe_join_text_blocks(blocks: List[str]) -> str:
    """
    Join text blocks safely, removing empties.
    """
    return "\n\n".join([b.strip() for b in blocks if b and b.strip()])


def compact_text(text: str, max_chars: int = 12000) -> str:
    """
    Compact text length before sending to model.
    """
    text = text.strip()
    if len(text) <= max_chars:
        return text
    return text[:max_chars]


def render_prompt(template: str, **kwargs: Any) -> str:
    """Render prompt variables without interpreting JSON braces in template text."""
    rendered = template
    for key, value in kwargs.items():
        rendered = rendered.replace('{' + key + '}', str(value))
    return rendered


# ============================================================
# 基础工具：LLM 调用
# ============================================================

def invoke_text(model: BaseChatModel, prompt: str, system_prompt: Optional[str] = None) -> str:
    """
    Invoke a chat model and return plain text content.

    We keep this intentionally simple so it works across many chat models.
    """
    messages = []
    if system_prompt:
        messages.append(SystemMessage(content=system_prompt))
    messages.append(HumanMessage(content=prompt))

    response = model.invoke(messages)

    # LangChain 常见返回格式处理
    if hasattr(response, "content"):
        if isinstance(response.content, str):
            return response.content
        if isinstance(response.content, list):
            # 某些模型 content 是 block list
            text_parts = []
            for item in response.content:
                if isinstance(item, dict):
                    txt = item.get("text")
                    if txt:
                        text_parts.append(txt)
                elif isinstance(item, str):
                    text_parts.append(item)
            return "\n".join(text_parts).strip()

    return str(response)


def invoke_json(model: BaseChatModel, prompt: str, system_prompt: Optional[str] = None) -> Any:
    """
    Invoke model and parse JSON output.
    """
    raw = invoke_text(model=model, prompt=prompt, system_prompt=system_prompt)
    return parse_json(raw)


def invoke_pydantic(
    model: BaseChatModel,
    prompt: str,
    schema: Type[T],
    system_prompt: Optional[str] = None,
) -> T:
    """
    Invoke model → parse JSON → validate into a Pydantic schema.
    """
    payload = invoke_json(model=model, prompt=prompt, system_prompt=system_prompt)
    return schema.model_validate(payload)


# ============================================================
# Source utilities
# ============================================================

def normalize_source_reference(raw: Dict[str, Any]) -> SourceReference:
    """
    Convert a raw source dict into SourceReference.
    """
    return SourceReference(
        title=raw.get("title"),
        organization=raw.get("organization") or raw.get("publisher"),
        url=raw.get("url"),
        publication_date=raw.get("publication_date") or raw.get("date"),
        access_date=raw.get("access_date"),
        source_type=raw.get("source_type"),
    )


def deduplicate_sources(sources: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Deduplicate raw sources by URL first, then by title.
    """
    seen_urls = set()
    seen_titles = set()
    result = []

    for item in sources:
        url = (item.get("url") or "").strip()
        title = (item.get("title") or "").strip().lower()

        if url and url in seen_urls:
            continue
        if not url and title and title in seen_titles:
            continue

        if url:
            seen_urls.add(url)
        if title:
            seen_titles.add(title)

        result.append(item)

    return result


# ============================================================
# 1. 主题拆解
# ============================================================

def decompose_topic(
    model: BaseChatModel,
    topic: str,
) -> Dict[str, Any]:
    """
    Break a broad topic into researchable subtopics.

    Returns:
        {
          "topic": "...",
          "subtopics": [
            {"title": "...", "purpose": "...", "priority": "..."}
          ]
        }
    """
    prompt = render_prompt(TOPIC_DECOMPOSITION_PROMPT, topic=topic)
    return invoke_json(model, prompt)


# ============================================================
# 2. 子题的收集策略
# ============================================================

def plan_source_collection(
    model: BaseChatModel,
    topic: str,
    subtopic: str,
) -> Dict[str, Any]:
    """
    Generate a source collection plan for a subtopic.
    """
    prompt = render_prompt(SOURCE_COLLECTION_PROMPT, topic=topic, subtopic=subtopic)
    return invoke_json(model, prompt)


# ============================================================
# 3. 单源摘要
# ============================================================

def summarize_source(
    model: BaseChatModel,
    text: str,
) -> Dict[str, Any]:
    """
    Summarize one source into structured intelligence notes.
    """
    prompt = render_prompt(SOURCE_SUMMARY_PROMPT, text=compact_text(text, max_chars=12000))
    return invoke_json(model, prompt)


# ============================================================
# 4. 抽取单个技术 / 项目 profile
# ============================================================

def extract_technology_profile(
    model: BaseChatModel,
    text: str,
) -> TechnologyProfile:
    """
    Extract a normalized TechnologyProfile from source material.
    """
    prompt = render_prompt(
        TECH_PROFILE_EXTRACTION_PROMPT,
        text=compact_text(text, max_chars=14000),
    )
    return invoke_pydantic(model, prompt, TechnologyProfile)


def extract_profiles_from_source_summaries(
    model: BaseChatModel,
    source_summaries: List[Dict[str, Any]],
) -> List[TechnologyProfile]:
    """
    Convert summarized source notes into TechnologyProfile objects.

    This is useful when you already compressed raw sources and want
    a second pass that normalizes cases.
    """
    profiles: List[TechnologyProfile] = []

    for item in source_summaries:
        text = json.dumps(item, ensure_ascii=False, indent=2)
        try:
            profile = extract_technology_profile(model, text)
            profiles.append(profile)
        except Exception:
            # 某个 source 失败时先跳过，后续可通过日志看
            continue

    return profiles


# ============================================================
# 5. 合并 / 去重 profiles
# ============================================================

def merge_profile_lists(
    existing: List[TechnologyProfile],
    incoming: List[TechnologyProfile],
) -> List[TechnologyProfile]:
    """
    Merge profile lists by name + company heuristic.

    This is a simple version. Future versions can add embedding
    or fuzzy matching.
    """
    result = list(existing)
    seen = set()

    for item in existing:
        key = (
            (item.name or "").strip().lower(),
            (item.company or item.institution or "").strip().lower(),
        )
        seen.add(key)

    for item in incoming:
        key = (
            (item.name or "").strip().lower(),
            (item.company or item.institution or "").strip().lower(),
        )
        if key in seen:
            continue
        seen.add(key)
        result.append(item)

    return result


# ============================================================
# 6. 案例对比
# ============================================================

def compare_cases(
    model: BaseChatModel,
    topic: str,
    cases: List[TechnologyProfile],
) -> ComparisonResult:
    """
    Compare multiple cases and return a structured comparison result.
    """
    case_payload = [case.model_dump(mode="json") for case in cases]
    prompt = render_prompt(
        CASE_COMPARISON_PROMPT,
        cases=json.dumps(case_payload, ensure_ascii=False, indent=2),
    )
    result = invoke_pydantic(model, prompt, ComparisonResult)
    if not result.topic:
        result.topic = topic
    return result


# ============================================================
# 7. 趋势分析
# ============================================================

def analyze_trends(
    model: BaseChatModel,
    topic: str,
    cases: List[TechnologyProfile],
    comparison: Optional[ComparisonResult] = None,
) -> TrendAnalysis:
    """
    Produce structured trend analysis.
    """
    material = {
        "cases": [case.model_dump(mode="json") for case in cases],
        "comparison": comparison.model_dump(mode="json") if comparison else None,
    }
    prompt = render_prompt(
        TREND_ANALYSIS_PROMPT,
        material=json.dumps(material, ensure_ascii=False, indent=2),
    )
    result = invoke_pydantic(model, prompt, TrendAnalysis)
    if not result.topic:
        result.topic = topic
    return result


# ============================================================
# 8. 编者按 / 短评
# ============================================================

def write_editorial_note(
    model: BaseChatModel,
    material: str,
) -> str:
    """
    Generate a short editorial-style note.
    """
    prompt = render_prompt(EDITORIAL_NOTE_PROMPT, material=compact_text(material, 12000))
    return invoke_text(model, prompt).strip()


# ============================================================
# 9. 案例对比表
# ============================================================

def generate_case_table(
    model: BaseChatModel,
    cases: List[TechnologyProfile],
) -> str:
    """
    Generate a markdown comparison table.
    """
    case_payload = [case.model_dump(mode="json") for case in cases]
    prompt = render_prompt(
        CASE_TABLE_PROMPT,
        cases=json.dumps(case_payload, ensure_ascii=False, indent=2),
    )
    return invoke_text(model, prompt).strip()


# ============================================================
# 10. 缺口分析
# ============================================================

def analyze_gaps(
    model: BaseChatModel,
    material: Dict[str, Any],
) -> List[IntelligenceGap]:
    """
    Identify intelligence gaps from current collected material.
    """
    prompt = render_prompt(
        GAP_ANALYSIS_PROMPT,
        material=json.dumps(material, ensure_ascii=False, indent=2),
    )
    payload = invoke_json(model, prompt)

    gap_items = payload.get("gaps", [])
    results: List[IntelligenceGap] = []

    for item in gap_items:
        try:
            results.append(IntelligenceGap.model_validate(item))
        except ValidationError:
            continue

    return results


# ============================================================
# 11. 最终报告
# ============================================================

def generate_final_report(
    model: BaseChatModel,
    topic: str,
    background: str,
    cases: List[TechnologyProfile],
    comparison: Optional[ComparisonResult],
    trend_analysis: Optional[TrendAnalysis],
    editorial_note: str,
    sources: List[SourceReference],
) -> str:
    """
    Generate the final markdown intelligence report.
    """
    case_payload = [case.model_dump(mode="json") for case in cases]
    comparison_payload = comparison.model_dump(mode="json") if comparison else {}
    trend_payload = trend_analysis.model_dump(mode="json") if trend_analysis else {}
    source_payload = [src.model_dump(mode="json") for src in sources]

    prompt = render_prompt(
        FINAL_REPORT_PROMPT,
        topic=topic,
        background=background,
        cases=json.dumps(case_payload, ensure_ascii=False, indent=2),
        comparison=json.dumps(comparison_payload, ensure_ascii=False, indent=2),
        trend_analysis=json.dumps(trend_payload, ensure_ascii=False, indent=2),
        editorial_note=editorial_note,
        sources=json.dumps(source_payload, ensure_ascii=False, indent=2),
    )

    return invoke_text(model, prompt).strip()


# ============================================================
# 12. 辅助：从 profiles 生成背景摘要
# ============================================================

def build_topic_background(cases: List[TechnologyProfile]) -> str:
    """
    Create a compact topic background summary from structured cases.

    This is intentionally rule-based rather than LLM-based, to provide
    a stable input into the final report.
    """
    if not cases:
        return "No structured cases available yet."

    energy_types = sorted(
        {
            c.energy_type.strip()
            for c in cases
            if c.energy_type and c.energy_type.strip()
        }
    )
    tech_routes = sorted(
        {
            c.tech_route.strip()
            for c in cases
            if c.tech_route and c.tech_route.strip()
        }
    )

    parts = []
    if energy_types:
        parts.append("Covered energy types: " + ", ".join(energy_types) + ".")
    if tech_routes:
        parts.append("Observed technology routes: " + ", ".join(tech_routes) + ".")

    maturity_counts: Dict[str, int] = {}
    for case in cases:
        key = (case.maturity or "unknown").strip().lower()
        maturity_counts[key] = maturity_counts.get(key, 0) + 1

    if maturity_counts:
        maturity_summary = ", ".join(
            f"{k}: {v}" for k, v in sorted(maturity_counts.items(), key=lambda x: x[0])
        )
        parts.append("Maturity distribution: " + maturity_summary + ".")

    return " ".join(parts)


# ============================================================
# 13. 辅助：从 raw source dicts 提取 SourceReference
# ============================================================

def extract_source_references(raw_sources: List[Dict[str, Any]]) -> List[SourceReference]:
    """
    Convert raw source dictionaries into normalized SourceReference list.
    """
    refs: List[SourceReference] = []
    for item in raw_sources:
        refs.append(normalize_source_reference(item))
    return refs