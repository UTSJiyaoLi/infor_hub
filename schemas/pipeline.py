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


# ------------------------------------------------------------------ #
#  Pipeline v3 新增模型
# ------------------------------------------------------------------ #

class EvidenceSignal(BaseModel):
    """A single evidence signal extracted from a document."""

    dimension: str = Field(
        ...,
        description="Which scoring dimension this signal supports: maturity, market, moat, scalability, cost, timing",
    )
    signal_type: str = Field(
        ...,
        description="Concrete signal type, e.g. sea_trial, grid_connection, tender, patent, mass_production",
    )
    description: str = Field(..., description="What happened")
    strength: int = Field(default=1, ge=1, le=5, description="Signal strength 1-5")
    source_doc_id: str = Field(default="", description="Source document id")
    source_url: str = Field(default="", description="Source URL")


class DimensionScores(BaseModel):
    """Six-dimension evaluation scores for a candidate direction."""

    maturity: int = Field(default=0, ge=0, le=100, description="技术成熟度：海试/并网/量产等硬里程碑")
    market: int = Field(default=0, ge=0, le=100, description="市场与政策：招标/订单/补贴/政策支持")
    moat: int = Field(default=0, ge=0, le=100, description="技术壁垒：专利/标准认证/独家技术")
    scalability: int = Field(default=0, ge=0, le=100, description="规模化潜力：模块化/可复制/产能规划")
    cost: int = Field(default=0, ge=0, le=100, description="成本趋势：LCOE下降/供应链成熟/批量制造")
    timing: int = Field(default=0, ge=0, le=100, description="时间窗口：近期密集信号/竞争格局/爆发前夜")
    rationale: str = Field(default="", description="评分依据的文字说明")


class EvaluatedCandidate(BaseModel):
    """A technology direction candidate with full evaluation."""

    candidate_id: str
    name: str
    description: str = ""
    tech_route: Optional[str] = None
    energy_type: Optional[str] = None
    profiles: List[Any] = Field(default_factory=list)  # TechnologyProfile dicts
    evidence_signals: List[EvidenceSignal] = Field(default_factory=list)
    dimension_scores: DimensionScores = Field(default_factory=DimensionScores)
    total_score: float = 0.0
    evidence_count: int = 0
    source_count: int = 0
    ranking: int = 0


class RankingResult(BaseModel):
    """Output of the ranking step."""

    candidates: List[EvaluatedCandidate] = Field(default_factory=list)
    top_candidate: Optional[EvaluatedCandidate] = None
    weights: Dict[str, float] = Field(default_factory=dict)
    threshold_score: float = 60.0
    threshold_sources: int = 2
