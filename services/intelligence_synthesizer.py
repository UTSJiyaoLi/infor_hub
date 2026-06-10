from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from langchain.chat_models import init_chat_model  # type: ignore[import-untyped]

from schemas.technology import (
    ComparisonDimension,
    ComparisonResult,
    IntelligenceGap,
    IntelligenceReportPackage,
    SourceReference,
    TechnologyProfile,
    TrendAnalysis,
)
from tools import parse_json


class IntelligenceSynthesizer:
    """Cluster profiles, compare cases, and synthesize trends + gaps via LLM."""

    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name or os.environ.get(
            "COLLECTOR_MODEL", "openai:gpt-4o"
        )
        self.model = init_chat_model(self.model_name)

    @staticmethod
    def _profile_summary(p: TechnologyProfile) -> str:
        """Compact text representation of a profile for LLM consumption."""
        parts = [
            f"Name: {p.name}",
        ]
        if p.company:
            parts.append(f"Company: {p.company}")
        if p.country:
            parts.append(f"Country: {p.country}")
        if p.energy_type:
            parts.append(f"Energy type: {p.energy_type}")
        if p.tech_route:
            parts.append(f"Tech route: {p.tech_route}")
        if p.capacity:
            parts.append(f"Capacity: {p.capacity}")
        if p.water_depth:
            parts.append(f"Water depth: {p.water_depth}")
        if p.maturity:
            parts.append(f"Maturity: {p.maturity}")
        if p.advantages:
            parts.append(f"Advantages: {'; '.join(p.advantages[:3])}")
        if p.limitations:
            parts.append(f"Limitations: {'; '.join(p.limitations[:3])}")
        if p.timeline:
            milestones = [f"{m.date}: {m.event}" for m in p.timeline[:3] if m.event]
            if milestones:
                parts.append(f"Timeline: {' | '.join(milestones)}")
        if p.significance:
            parts.append(f"Significance: {p.significance[:200]}")
        return "\n".join(parts)

    def cluster_profiles(
        self, profiles: List[TechnologyProfile]
    ) -> Dict[str, List[TechnologyProfile]]:
        """Simple clustering by tech_route, falling back to energy_type."""
        clusters: Dict[str, List[TechnologyProfile]] = {}
        for p in profiles:
            key = (p.tech_route or p.energy_type or "其他").strip()
            clusters.setdefault(key, []).append(p)
        return clusters

    def synthesize_comparison(
        self, profiles: List[TechnologyProfile], topic: str
    ) -> ComparisonResult:
        if len(profiles) < 2:
            return ComparisonResult(topic=topic)

        summaries = [self._profile_summary(p) for p in profiles]
        prompt = (
            "You are a senior engineering intelligence analyst.\n\n"
            f"Topic: {topic}\n\n"
            "Given the following technology/project profiles, produce a structured comparison.\n\n"
            "Profiles:\n"
            "---\n"
            + "\n---\n".join(summaries[:15])
            + "\n---\n\n"
            "Return strict JSON matching this schema:\n"
            '{\n'
            '  "included_cases": ["case name 1", "case name 2"],\n'
            '  "dimensions": [\n'
            '    {"dimension": "...", "observation": "...", "stronger_cases": ["..."], "weaker_cases": ["..."], "note": "..."}\n'
            '  ],\n'
            '  "key_differences": ["..."],\n'
            '  "notable_patterns": ["..."],\n'
            '  "commercialization_observation": "...",\n'
            '  "engineering_observation": "...",\n'
            '  "open_questions": ["..."]\n'
            "}\n"
        )
        return self._invoke_structured(prompt, ComparisonResult, default=ComparisonResult(topic=topic))

    def synthesize_trends(
        self, profiles: List[TechnologyProfile], topic: str
    ) -> TrendAnalysis:
        if not profiles:
            return TrendAnalysis(topic=topic)

        summaries = [self._profile_summary(p) for p in profiles]
        prompt = (
            "You are a strategic technology analyst.\n\n"
            f"Topic: {topic}\n\n"
            "Based on the following collected cases, synthesize industry trends.\n\n"
            "Cases:\n"
            "---\n"
            + "\n---\n".join(summaries[:15])
            + "\n---\n\n"
            "Return strict JSON matching this schema:\n"
            '{\n'
            '  "observed_trends": ["..."],\n'
            '  "bottlenecks": ["..."],\n'
            '  "opportunity_areas": ["..."],\n'
            '  "watchpoints": ["..."],\n'
            '  "editorial_note": "..."\n'
            "}\n"
        )
        return self._invoke_structured(prompt, TrendAnalysis, default=TrendAnalysis(topic=topic))

    def identify_gaps(
        self, profiles: List[TechnologyProfile], topic: str
    ) -> List[IntelligenceGap]:
        if not profiles:
            return []

        summaries = [self._profile_summary(p) for p in profiles]
        prompt = (
            "You are a critical intelligence reviewer.\n\n"
            f"Topic: {topic}\n\n"
            "Review the following collected cases and identify information gaps.\n\n"
            "Cases:\n"
            "---\n"
            + "\n---\n".join(summaries[:15])
            + "\n---\n\n"
            "Return strict JSON:\n"
            '{\n'
            '  "gaps": [\n'
            '    {"gap": "...", "why_it_matters": "...", "priority": "high|medium|low"}\n'
            '  ]\n'
            "}\n"
        )
        try:
            raw = self.model.invoke(prompt)
            content = raw.content if hasattr(raw, "content") else str(raw)
            parsed = parse_json(content)
            if isinstance(parsed, dict):
                rows = parsed.get("gaps", [])
                return [IntelligenceGap.model_validate(row) for row in rows if isinstance(row, dict)]
        except Exception:
            pass
        return []

    def synthesize(
        self, profiles: List[TechnologyProfile], topic: str
    ) -> IntelligenceReportPackage:
        comparison = self.synthesize_comparison(profiles, topic)
        trends = self.synthesize_trends(profiles, topic)
        gaps = self.identify_gaps(profiles, topic)

        # Deduplicate and collect all sources
        all_sources: List[SourceReference] = []
        seen_urls: set[str] = set()
        for p in profiles:
            for s in p.sources:
                url = s.url or ""
                if url and url in seen_urls:
                    continue
                if url:
                    seen_urls.add(url)
                all_sources.append(s)

        return IntelligenceReportPackage(
            topic=topic,
            cases=profiles,
            comparison=comparison,
            trend_analysis=trends,
            gaps=gaps,
            sources=all_sources,
        )

    def _invoke_structured(
        self,
        prompt: str,
        schema_cls: Any,
        default: Any,
    ) -> Any:
        """Try structured output, fall back to manual parse."""
        try:
            structured = self.model.with_structured_output(schema_cls)
            result = structured.invoke(prompt)
            if isinstance(result, schema_cls):
                return result
        except Exception:
            pass

        try:
            raw = self.model.invoke(prompt)
            content = raw.content if hasattr(raw, "content") else str(raw)
            parsed = parse_json(content)
            if isinstance(parsed, dict):
                return schema_cls.model_validate(parsed)
        except Exception:
            pass

        return default
