from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from langgraph.graph import StateGraph, END

from state import CollectorState
from schemas.technology import TechnologyProfile
from tools import (
    decompose_topic,
    plan_source_collection,
    summarize_source,
    extract_profiles_from_source_summaries,
    merge_profile_lists,
    compare_cases,
    analyze_trends,
    write_editorial_note,
    generate_case_table,
    analyze_gaps,
    generate_final_report,
    build_topic_background,
    deduplicate_sources,
    extract_source_references,
)


# ============================================================
# Helper functions
# ============================================================

def _ensure_list(value: Optional[List[Any]]) -> List[Any]:
    if value is None:
        return []
    return value


def _append_log(state: CollectorState, message: str) -> Dict[str, Any]:
    logs = list(_ensure_list(state.get("logs")))
    logs.append(message)
    return {"logs": logs}


def _set_step(step_name: str) -> Dict[str, Any]:
    return {"current_step": step_name}


# ============================================================
# Node 1: Initialize
# ============================================================

def initialize_state(state: CollectorState) -> Dict[str, Any]:
    """
    Initialize missing fields so downstream nodes can rely on them.
    """
    updates: Dict[str, Any] = {
        "subtopics": _ensure_list(state.get("subtopics")),
        "raw_queries": _ensure_list(state.get("raw_queries")),
        "raw_sources": _ensure_list(state.get("raw_sources")),
        "source_summaries": _ensure_list(state.get("source_summaries")),
        "technology_profiles": _ensure_list(state.get("technology_profiles")),
        "gaps": _ensure_list(state.get("gaps")),
        "sources": _ensure_list(state.get("sources")),
        "logs": _ensure_list(state.get("logs")),
        "iteration_count": state.get("iteration_count", 0),
        "current_step": "initialize",
    }

    logs = list(updates["logs"])
    logs.append(f"Initialized workflow for topic: {state.get('topic', '')}")
    updates["logs"] = logs
    return updates


# ============================================================
# Node 2: Decompose topic
# ============================================================

def topic_decomposition_node(state: CollectorState) -> Dict[str, Any]:
    """
    Use the LLM to decompose the topic into researchable subtopics.
    """
    model = state["model"]  # injected at runtime
    topic = state["topic"]

    result = decompose_topic(model=model, topic=topic)
    subtopics = result.get("subtopics", [])

    updates: Dict[str, Any] = {
        "subtopics": subtopics,
        "current_step": "topic_decomposition",
    }

    logs = list(_ensure_list(state.get("logs")))
    logs.append(f"Decomposed topic into {len(subtopics)} subtopics.")
    updates["logs"] = logs
    return updates


# ============================================================
# Node 3: Plan source collection
# ============================================================

def source_planning_node(state: CollectorState) -> Dict[str, Any]:
    """
    For each subtopic, generate a source collection plan and raw queries.
    """
    model = state["model"]
    topic = state["topic"]
    subtopics = _ensure_list(state.get("subtopics"))

    plans: List[Dict[str, Any]] = []
    raw_queries: List[str] = []

    for sub in subtopics:
        title = sub.get("title", "")
        if not title:
            continue

        plan = plan_source_collection(
            model=model,
            topic=topic,
            subtopic=title,
        )
        plans.append(plan)

        key_questions = plan.get("key_questions", [])
        if key_questions:
            raw_queries.extend(key_questions)
        else:
            raw_queries.append(title)

    updates: Dict[str, Any] = {
        "collection_plans": plans,
        "raw_queries": raw_queries,
        "current_step": "source_planning",
    }

    logs = list(_ensure_list(state.get("logs")))
    logs.append(f"Planned source collection for {len(subtopics)} subtopics.")
    updates["logs"] = logs
    return updates


# ============================================================
# Node 4: Ingest existing raw sources
# ============================================================

def source_ingestion_node(state: CollectorState) -> Dict[str, Any]:
    """
    Normalize and deduplicate already-provided raw sources.

    Note:
    This workflow assumes raw_sources may already be injected by the caller
    from:
    - uploaded docs
    - manual corpus
    - a future fetcher/search stage
    """
    raw_sources = deduplicate_sources(_ensure_list(state.get("raw_sources")))
    sources = extract_source_references(raw_sources)

    updates: Dict[str, Any] = {
        "raw_sources": raw_sources,
        "sources": sources,
        "current_step": "source_ingestion",
    }

    logs = list(_ensure_list(state.get("logs")))
    logs.append(f"Ingested {len(raw_sources)} raw sources after deduplication.")
    updates["logs"] = logs
    return updates


# ============================================================
# Node 5: Summarize sources
# ============================================================

def source_summary_node(state: CollectorState) -> Dict[str, Any]:
    """
    Summarize each raw source into a structured source summary.
    """
    model = state["model"]
    raw_sources = _ensure_list(state.get("raw_sources"))

    source_summaries: List[Dict[str, Any]] = []
    logs = list(_ensure_list(state.get("logs")))

    for idx, src in enumerate(raw_sources):
        text = (src.get("text") or "").strip()
        if not text:
            logs.append(f"Skipped raw source {idx}: empty text.")
            continue

        try:
            summary = summarize_source(model=model, text=text)
            if src.get("url"):
                summary["url"] = src.get("url")
            if src.get("title") and not summary.get("source_title"):
                summary["source_title"] = src.get("title")
            source_summaries.append(summary)
        except Exception as exc:
            logs.append(f"Failed to summarize source {idx}: {exc}")

    updates: Dict[str, Any] = {
        "source_summaries": source_summaries,
        "current_step": "source_summary",
        "logs": logs,
    }
    logs.append(f"Generated {len(source_summaries)} source summaries.")
    return updates


# ============================================================
# Node 6: Extract structured profiles
# ============================================================

def profile_extraction_node(state: CollectorState) -> Dict[str, Any]:
    """
    Convert source summaries into normalized TechnologyProfile objects.
    """
    model = state["model"]
    source_summaries = _ensure_list(state.get("source_summaries"))
    existing_profiles = _ensure_list(state.get("technology_profiles"))

    incoming_profiles = extract_profiles_from_source_summaries(
        model=model,
        source_summaries=source_summaries,
    )

    merged_profiles = merge_profile_lists(existing_profiles, incoming_profiles)

    logs = list(_ensure_list(state.get("logs")))
    logs.append(
        f"Extracted {len(incoming_profiles)} profiles; total after merge: {len(merged_profiles)}."
    )

    return {
        "technology_profiles": merged_profiles,
        "current_step": "profile_extraction",
        "logs": logs,
    }


# ============================================================
# Node 7: Comparison
# ============================================================

def comparison_node(state: CollectorState) -> Dict[str, Any]:
    """
    Compare structured profiles if enough cases exist.
    """
    model = state["model"]
    topic = state["topic"]
    profiles = _ensure_list(state.get("technology_profiles"))

    logs = list(_ensure_list(state.get("logs")))

    if len(profiles) < 2:
        logs.append("Skipped comparison: fewer than 2 profiles available.")
        return {
            "comparison": None,
            "current_step": "comparison",
            "logs": logs,
        }

    try:
        comparison = compare_cases(model=model, topic=topic, cases=profiles)
        logs.append("Generated case comparison.")
        return {
            "comparison": comparison,
            "current_step": "comparison",
            "logs": logs,
        }
    except Exception as exc:
        logs.append(f"Comparison failed: {exc}")
        return {
            "comparison": None,
            "current_step": "comparison",
            "logs": logs,
        }


# ============================================================
# Node 8: Trend analysis
# ============================================================

def trend_analysis_node(state: CollectorState) -> Dict[str, Any]:
    """
    Analyze trends across collected cases.
    """
    model = state["model"]
    topic = state["topic"]
    profiles = _ensure_list(state.get("technology_profiles"))
    comparison = state.get("comparison")

    logs = list(_ensure_list(state.get("logs")))

    if not profiles:
        logs.append("Skipped trend analysis: no profiles available.")
        return {
            "trend_analysis": None,
            "current_step": "trend_analysis",
            "logs": logs,
        }

    try:
        trend = analyze_trends(
            model=model,
            topic=topic,
            cases=profiles,
            comparison=comparison,
        )
        logs.append("Generated trend analysis.")
        return {
            "trend_analysis": trend,
            "current_step": "trend_analysis",
            "logs": logs,
        }
    except Exception as exc:
        logs.append(f"Trend analysis failed: {exc}")
        return {
            "trend_analysis": None,
            "current_step": "trend_analysis",
            "logs": logs,
        }


# ============================================================
# Node 9: Case table
# ============================================================

def case_table_node(state: CollectorState) -> Dict[str, Any]:
    """
    Generate a compact markdown table for quick comparison.
    """
    model = state["model"]
    profiles = _ensure_list(state.get("technology_profiles"))

    logs = list(_ensure_list(state.get("logs")))

    if not profiles:
        logs.append("Skipped case table generation: no profiles available.")
        return {
            "case_table": "",
            "current_step": "case_table",
            "logs": logs,
        }

    try:
        table = generate_case_table(model=model, cases=profiles)
        logs.append("Generated case comparison table.")
        return {
            "case_table": table,
            "current_step": "case_table",
            "logs": logs,
        }
    except Exception as exc:
        logs.append(f"Case table generation failed: {exc}")
        return {
            "case_table": "",
            "current_step": "case_table",
            "logs": logs,
        }


# ============================================================
# Node 10: Gap analysis
# ============================================================

def gap_analysis_node(state: CollectorState) -> Dict[str, Any]:
    """
    Identify intelligence gaps from the currently collected material.
    """
    model = state["model"]

    material = {
        "topic": state.get("topic"),
        "subtopics": state.get("subtopics"),
        "profiles": [
            p.model_dump(mode="json") if hasattr(p, "model_dump") else p
            for p in _ensure_list(state.get("technology_profiles"))
        ],
        "comparison": state.get("comparison").model_dump(mode="json")
        if state.get("comparison")
        else None,
        "trend_analysis": state.get("trend_analysis").model_dump(mode="json")
        if state.get("trend_analysis")
        else None,
    }

    logs = list(_ensure_list(state.get("logs")))

    try:
        gaps = analyze_gaps(model=model, material=material)
        logs.append(f"Identified {len(gaps)} intelligence gaps.")
        return {
            "gaps": gaps,
            "current_step": "gap_analysis",
            "logs": logs,
        }
    except Exception as exc:
        logs.append(f"Gap analysis failed: {exc}")
        return {
            "gaps": [],
            "current_step": "gap_analysis",
            "logs": logs,
        }


# ============================================================
# Node 11: Editorial note
# ============================================================

def editorial_note_node(state: CollectorState) -> Dict[str, Any]:
    """
    Write a short editorial-style note.
    """
    model = state["model"]
    topic = state["topic"]
    profiles = _ensure_list(state.get("technology_profiles"))
    comparison = state.get("comparison")
    trend = state.get("trend_analysis")

    material_blocks = [
        f"Topic: {topic}",
        "Profiles:",
        json.dumps(
            [p.model_dump(mode="json") for p in profiles],
            ensure_ascii=False,
            indent=2,
        ) if profiles else "",
        "Comparison:",
        json.dumps(comparison.model_dump(mode="json"), ensure_ascii=False, indent=2)
        if comparison else "",
        "Trend:",
        json.dumps(trend.model_dump(mode="json"), ensure_ascii=False, indent=2)
        if trend else "",
    ]
    material = "\n\n".join([b for b in material_blocks if b])

    logs = list(_ensure_list(state.get("logs")))

    try:
        note = write_editorial_note(model=model, material=material)
        logs.append("Generated editorial note.")
        return {
            "editorial_note": note,
            "current_step": "editorial_note",
            "logs": logs,
        }
    except Exception as exc:
        logs.append(f"Editorial note generation failed: {exc}")
        return {
            "editorial_note": "",
            "current_step": "editorial_note",
            "logs": logs,
        }


# ============================================================
# Node 12: Final report
# ============================================================

def final_report_node(state: CollectorState) -> Dict[str, Any]:
    """
    Generate final markdown report.
    """
    model = state["model"]
    topic = state["topic"]
    profiles = _ensure_list(state.get("technology_profiles"))
    comparison = state.get("comparison")
    trend = state.get("trend_analysis")
    sources = _ensure_list(state.get("sources"))
    editorial_note = state.get("editorial_note") or ""

    background = build_topic_background(profiles)

    logs = list(_ensure_list(state.get("logs")))

    try:
        report = generate_final_report(
            model=model,
            topic=topic,
            background=background,
            cases=profiles,
            comparison=comparison,
            trend_analysis=trend,
            editorial_note=editorial_note,
            sources=sources,
        )
        logs.append("Generated final report.")
        return {
            "final_report": report,
            "current_step": "final_report",
            "logs": logs,
        }
    except Exception as exc:
        logs.append(f"Final report generation failed: {exc}")
        return {
            "final_report": "",
            "current_step": "final_report",
            "logs": logs,
        }


# ============================================================
# Router / Conditions
# ============================================================

def should_continue_after_profiles(state: CollectorState) -> str:
    """
    Decide whether to continue analysis after profile extraction.
    """
    profiles = _ensure_list(state.get("technology_profiles"))
    if profiles:
        return "comparison"
    return "gap_analysis"


# ============================================================
# Graph builder
# ============================================================

def build_research_graph():
    """
    Build the main intelligence collection workflow graph.
    """
    graph = StateGraph(CollectorState)

    # Nodes
    graph.add_node("initialize", initialize_state)
    graph.add_node("topic_decomposition", topic_decomposition_node)
    graph.add_node("source_planning", source_planning_node)
    graph.add_node("source_ingestion", source_ingestion_node)
    graph.add_node("source_summary", source_summary_node)
    graph.add_node("profile_extraction", profile_extraction_node)
    graph.add_node("comparison", comparison_node)
    graph.add_node("trend_analysis", trend_analysis_node)
    graph.add_node("case_table", case_table_node)
    graph.add_node("gap_analysis", gap_analysis_node)
    graph.add_node("editorial_note", editorial_note_node)
    graph.add_node("final_report", final_report_node)

    # Entry
    graph.set_entry_point("initialize")

    # Edges
    graph.add_edge("initialize", "topic_decomposition")
    graph.add_edge("topic_decomposition", "source_planning")
    graph.add_edge("source_planning", "source_ingestion")
    graph.add_edge("source_ingestion", "source_summary")
    graph.add_edge("source_summary", "profile_extraction")

    graph.add_conditional_edges(
        "profile_extraction",
        should_continue_after_profiles,
        {
            "comparison": "comparison",
            "gap_analysis": "gap_analysis",
        },
    )

    graph.add_edge("comparison", "trend_analysis")
    graph.add_edge("trend_analysis", "case_table")
    graph.add_edge("case_table", "gap_analysis")
    graph.add_edge("gap_analysis", "editorial_note")
    graph.add_edge("editorial_note", "final_report")
    graph.add_edge("final_report", END)

    return graph.compile()