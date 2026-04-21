from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class SourceSpec(BaseModel):
    source_id: str
    name: str
    domain: str
    source_type: str
    entry_urls: List[str] = Field(default_factory=list)
    fetch_method: str = "static_html"
    update_frequency: str = "weekly"
    credibility: str = "medium"
    tags: List[str] = Field(default_factory=list)
    enabled: bool = True


class NormalizedDocument(BaseModel):
    doc_id: str
    title: str
    published_at: Optional[str] = None
    source: str
    url: str = ""
    body_markdown: str
    summary: str = ""
    language: str = "unknown"
    doc_type: str = "web"
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SignalItem(BaseModel):
    signal_type: str
    value: str
    strength: int = 1
    evidence_doc_id: str
    evidence_snippet: str


class CandidateDirection(BaseModel):
    candidate_id: str
    name: str
    description: str
    entity_tags: List[str] = Field(default_factory=list)
    representative_evidence: List[SignalItem] = Field(default_factory=list)
    related_doc_ids: List[str] = Field(default_factory=list)


class DirectionScore(BaseModel):
    candidate_id: str
    growth: int
    feasibility: int
    synergy: int
    moat: int
    timing: int
    total: int
    rationale: List[str] = Field(default_factory=list)

