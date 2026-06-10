from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from langchain.chat_models import init_chat_model  # type: ignore[import-untyped]

from schemas.pipeline import (
    DimensionScores,
    DirectionScore,
    EvaluatedCandidate,
    EvidenceSignal,
    RankingResult,
)
from schemas.technology import TechnologyProfile
from tools import parse_json


# ------------------------------------------------------------------ #
# Legacy v2 scoring (kept for backward compatibility with pipeline_v2)
# ------------------------------------------------------------------ #

def _clip_0_20(v: int) -> int:
    return max(0, min(20, v))


def score_candidates(dossiers: dict[str, dict]) -> list[DirectionScore]:
    rows: list[DirectionScore] = []
    for cid, ds in dossiers.items():
        candidate = ds.get("candidate", {})
        tags = list(candidate.get("entity_tags") or [])
        doc_count = int(ds.get("doc_count") or 0)
        source_count = len(ds.get("sources") or [])

        growth = _clip_0_20(8 + doc_count * 2)
        feasibility = _clip_0_20(6 + (4 if "maturity" in tags else 0) + min(8, source_count))
        synergy = _clip_0_20(6 + (6 if "synergy" in tags else 1) + min(6, len(tags)))
        moat = _clip_0_20(5 + (8 if "standard_certification" in tags else 0) + min(7, source_count))
        timing = _clip_0_20(7 + (6 if "funding_support" in tags else 0) + min(5, doc_count))

        total = growth + feasibility + synergy + moat + timing
        rationale = [
            f"证据文档数={doc_count}",
            f"来源数量={source_count}",
            f"信号标签={','.join(tags) if tags else 'none'}",
        ]
        rows.append(
            DirectionScore(
                candidate_id=cid,
                growth=growth,
                feasibility=feasibility,
                synergy=synergy,
                moat=moat,
                timing=timing,
                total=total,
                rationale=rationale,
            )
        )
    rows.sort(key=lambda x: x.total, reverse=True)
    return rows


# ------------------------------------------------------------------ #
# TIDE v3 scoring engine
# ------------------------------------------------------------------ #

DEFAULT_WEIGHTS = {
    "maturity": 0.20,
    "market": 0.20,
    "moat": 0.15,
    "scalability": 0.15,
    "cost": 0.15,
    "timing": 0.15,
}


class ScoringEngine:
    """
    Six-dimension scoring + ranking for technology candidates.

    Algorithm:
    1. For each candidate, feed all evidence signals + profiles to LLM
    2. LLM outputs 6 dimension scores (0-100) + rationale
    3. Weighted total = sum(dim_score * weight)
    4. Rank by total score descending
    5. Select top candidate if it meets thresholds
    """

    def __init__(
        self,
        model_name: Optional[str] = None,
        weights: Optional[Dict[str, float]] = None,
        threshold_score: float = 60.0,
        threshold_sources: int = 2,
    ):
        self.model_name = model_name or os.environ.get(
            "COLLECTOR_MODEL", "openai:gpt-4o"
        )
        self.model = init_chat_model(self.model_name)
        self.weights = weights or dict(DEFAULT_WEIGHTS)
        self.threshold_score = threshold_score
        self.threshold_sources = threshold_sources

    @staticmethod
    def _candidate_summary(candidate: Dict[str, Any]) -> str:
        """Build a compact text summary of a candidate for the LLM prompt."""
        lines = [
            f"候选方向: {candidate['name']}",
            f"技术路线: {candidate.get('tech_route', '未分类')}",
            f"能源类型: {candidate.get('energy_type', '未分类')}",
        ]

        profiles: List[TechnologyProfile] = candidate.get("profiles", [])
        if profiles:
            lines.append("收录案例:")
            for p in profiles[:5]:
                parts = [p.name]
                if p.company:
                    parts.append(f"公司:{p.company}")
                if p.country:
                    parts.append(f"国家:{p.country}")
                if p.capacity:
                    parts.append(f"容量:{p.capacity}")
                if p.maturity:
                    parts.append(f"成熟度:{p.maturity}")
                lines.append(f"  - {' | '.join(parts)}")

        signals: List[EvidenceSignal] = candidate.get("signals", [])
        if signals:
            lines.append("证据信号:")
            for s in signals[:10]:
                lines.append(f"  [{s.dimension}] {s.signal_type}: {s.description} (强度{s.strength})")

        return "\n".join(lines)

    def _score_single(self, candidate: Dict[str, Any]) -> DimensionScores:
        summary = self._candidate_summary(candidate)
        prompt = (
            "你是一名资深技术投资评估专家。请基于以下证据，对候选技术方向进行六维度评分。\n\n"
            f"{summary}\n\n"
            "评分维度（每个0-100）：\n"
            "1. maturity(技术成熟度): 是否有海试、并网、量产、TRL提升等硬里程碑\n"
            "2. market(市场与政策): 是否有招标、大额订单、政府补贴、政策支持\n"
            "3. moat(技术壁垒): 是否有专利、标准认证(DNV/AiP)、独家技术\n"
            "4. scalability(规模化潜力): 是否模块化、可复制、有产能扩张计划\n"
            "5. cost(成本趋势): LCOE是否下降、供应链是否成熟、能否批量制造\n"
            "6. timing(时间窗口): 近期是否有密集信号、是否处于爆发前夜\n\n"
            "评分原则：\n"
            "- 只基于提供的证据打分，不要引入外部知识\n"
            "- 证据不足的方向相应维度给低分\n"
            "- 给出每个维度的具体评分理由\n\n"
            "Return strict JSON only:\n"
            '{\n'
            '  "maturity": 75,\n'
            '  "market": 60,\n'
            '  "moat": 45,\n'
            '  "scalability": 70,\n'
            '  "cost": 55,\n'
            '  "timing": 80,\n'
            '  "rationale": "评分理由..."\n'
            '}'
        )

        # Try structured output first
        try:
            structured = self.model.with_structured_output(DimensionScores)
            result = structured.invoke(prompt)
            if isinstance(result, DimensionScores):
                return result
        except Exception:
            pass

        # Fallback: plain invoke + manual parse
        try:
            raw = self.model.invoke(prompt)
            content = raw.content if hasattr(raw, "content") else str(raw)
            parsed = parse_json(content)
            if isinstance(parsed, dict):
                return DimensionScores.model_validate(parsed)
        except Exception:
            pass

        return DimensionScores()

    def evaluate(self, candidates: List[Dict[str, Any]]) -> RankingResult:
        evaluated: List[EvaluatedCandidate] = []

        for c in candidates:
            dim_scores = self._score_single(c)
            total = sum(
                getattr(dim_scores, dim, 0) * weight
                for dim, weight in self.weights.items()
            )

            # Count unique source URLs
            docs = c.get("documents", [])
            unique_urls = {d.get("url", "") for d in docs if d.get("url")}

            ec = EvaluatedCandidate(
                candidate_id=c["candidate_id"],
                name=c["name"],
                description=f"{c.get('tech_route', '')} 方向的 {c['name']}",
                tech_route=c.get("tech_route") or None,
                energy_type=c.get("energy_type") or None,
                profiles=[p.model_dump(mode="json") for p in c.get("profiles", [])],
                evidence_signals=c.get("signals", []),
                dimension_scores=dim_scores,
                total_score=round(total, 1),
                evidence_count=len(docs),
                source_count=len(unique_urls),
            )
            evaluated.append(ec)

        # Sort by total score descending
        evaluated.sort(key=lambda x: x.total_score, reverse=True)
        for i, ec in enumerate(evaluated, start=1):
            ec.ranking = i

        # Select top candidate
        top = None
        for ec in evaluated:
            if ec.total_score >= self.threshold_score and ec.source_count >= self.threshold_sources:
                top = ec
                break

        return RankingResult(
            candidates=evaluated,
            top_candidate=top,
            weights=self.weights,
            threshold_score=self.threshold_score,
            threshold_sources=self.threshold_sources,
        )
