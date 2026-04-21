from __future__ import annotations

from typing import Any, Dict, List, Optional, TypedDict

from langchain_core.language_models.chat_models import BaseChatModel

from schemas.technology import (
    ComparisonResult,
    IntelligenceGap,
    SourceReference,
    TechnologyProfile,
    TrendAnalysis,
)


class CollectorState(TypedDict, total=False):
    # Inputs
    topic: str
    user_goal: str
    model: BaseChatModel
    raw_sources: List[Dict[str, Any]]

    # Intermediate artifacts
    subtopics: List[Dict[str, Any]]
    raw_queries: List[str]
    collection_plans: List[Dict[str, Any]]
    source_summaries: List[Dict[str, Any]]
    technology_profiles: List[TechnologyProfile]
    sources: List[SourceReference]
    comparison: Optional[ComparisonResult]
    trend_analysis: Optional[TrendAnalysis]
    case_table: str
    gaps: List[IntelligenceGap]
    editorial_note: str
    background: str

    # Outputs
    final_report: str

    # Runtime metadata
    current_step: str
    iteration_count: int
    logs: List[str]
