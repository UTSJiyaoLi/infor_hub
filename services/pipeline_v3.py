from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Generator, List, Optional

from schemas.pipeline import RankingResult
from schemas.technology import TechnologyProfile
from services.candidate_aggregator import CandidateAggregator
from services.content_analyzer import ContentAnalyzer
from services.report_builder import ReportBuilder
from services.scoring_engine import ScoringEngine
from services.search_orchestrator import create_search_orchestrator
from services.signal_extractor_v2 import SignalExtractorV2
from settings import settings


@dataclass
class PipelineV3Result:
    raw_sources: List[Dict[str, Any]]
    profiles: List[TechnologyProfile]
    ranking: RankingResult
    final_report: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "raw_sources": self.raw_sources,
            "profiles": [p.model_dump(mode="json") for p in self.profiles],
            "ranking": self.ranking.model_dump(mode="json"),
            "final_report": self.final_report,
        }


def _build_search_query(topic: str, user_goal: str = "") -> str:
    base = f"{topic} latest breakthrough commercialization 2025 2026"
    if user_goal:
        base = f"{topic} {user_goal}"
    return base


def run_intelligence_pipeline_v3(
    topic: str,
    user_goal: str = "",
    raw_sources: Optional[List[Dict[str, Any]]] = None,
    time_window_days: Optional[int] = None,
    max_search_results: Optional[int] = None,
) -> PipelineV3Result:
    # Phase 1: Search
    if not raw_sources:
        orchestrator = create_search_orchestrator(
            backend_name=settings.search_backend,
            include_domains=settings.default_include_domains,
        )
        query = _build_search_query(topic, user_goal)
        sources = orchestrator.search_and_fetch(
            query=query,
            max_results=max_search_results or settings.max_search_results,
            time_window_days=time_window_days or settings.default_time_window_days,
        )
    else:
        sources = list(raw_sources)

    # Phase 2: Extract TechnologyProfiles
    analyzer = ContentAnalyzer(model_name=settings.collector_model)
    profiles = analyzer.analyze_batch(sources, topic=topic)

    # Phase 3: Extract EvidenceSignals
    extractor = SignalExtractorV2(model_name=settings.collector_model)
    signals = extractor.extract_batch(sources, topic=topic)

    # Phase 4: Aggregate into candidates
    aggregator = CandidateAggregator()
    candidates = aggregator.aggregate(profiles, signals, sources)

    # Phase 5: Score & Rank
    engine = ScoringEngine(model_name=settings.collector_model)
    ranking = engine.evaluate(candidates)

    # Phase 6: Build Top-1 deep report
    builder = ReportBuilder()
    report = builder.build_top1_report(ranking, user_goal=user_goal)

    return PipelineV3Result(
        raw_sources=sources,
        profiles=profiles,
        ranking=ranking,
        final_report=report,
    )


def stream_report_events_v3(
    topic: str,
    user_goal: str = "",
    raw_sources: Optional[List[Dict[str, Any]]] = None,
    time_window_days: Optional[int] = None,
    max_search_results: Optional[int] = None,
) -> Generator[Dict[str, Any], None, PipelineV3Result]:
    # Phase: search
    yield {"phase": "search", "message": "searching for latest sources"}
    if not raw_sources:
        orchestrator = create_search_orchestrator(
            backend_name=settings.search_backend,
            include_domains=settings.default_include_domains,
        )
        query = _build_search_query(topic, user_goal)
        sources = orchestrator.search_and_fetch(
            query=query,
            max_results=max_search_results or settings.max_search_results,
            time_window_days=time_window_days or settings.default_time_window_days,
        )
    else:
        sources = list(raw_sources)
    yield {"phase": "search", "source_count": len(sources)}

    # Phase: profile extraction
    yield {"phase": "profile", "message": "extracting technology profiles"}
    analyzer = ContentAnalyzer(model_name=settings.collector_model)
    profiles = analyzer.analyze_batch(sources, topic=topic)
    yield {"phase": "profile", "profile_count": len(profiles)}

    # Phase: signal extraction
    yield {"phase": "signal", "message": "extracting evidence signals"}
    extractor = SignalExtractorV2(model_name=settings.collector_model)
    signals = extractor.extract_batch(sources, topic=topic)
    yield {"phase": "signal", "signal_count": len(signals)}

    # Phase: aggregation
    yield {"phase": "aggregate", "message": "aggregating candidates"}
    aggregator = CandidateAggregator()
    candidates = aggregator.aggregate(profiles, signals, sources)
    yield {"phase": "aggregate", "candidate_count": len(candidates)}

    # Phase: scoring
    yield {"phase": "score", "message": "scoring candidates"}
    engine = ScoringEngine(model_name=settings.collector_model)
    ranking = engine.evaluate(candidates)
    yield {
        "phase": "score",
        "ranked_count": len(ranking.candidates),
        "top_score": ranking.top_candidate.total_score if ranking.top_candidate else 0,
    }

    # Phase: report
    yield {"phase": "report", "message": "generating Top-1 deep report"}
    builder = ReportBuilder()
    report = builder.build_top1_report(ranking, user_goal=user_goal)

    result = PipelineV3Result(
        raw_sources=sources,
        profiles=profiles,
        ranking=ranking,
        final_report=report,
    )
    yield {"phase": "done", "message": "report ready"}
    return result
