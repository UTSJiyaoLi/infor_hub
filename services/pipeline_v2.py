from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Generator, List

from schemas.pipeline import CandidateDirection, DirectionScore, NormalizedDocument, SignalItem
from services.candidate_discovery import discover_candidates
from services.collector import collect_raw_items
from services.evidence_builder import build_direction_dossiers
from services.parser_normalizer import normalize_documents
from services.report_agent import build_markdown_report
from services.scoring_engine import score_candidates
from services.signal_extractor import extract_signals
from services.source_registry import load_source_registry
from settings import settings


@dataclass
class PipelineResult:
    raw_sources: List[Dict[str, Any]]
    documents: List[NormalizedDocument]
    signals: List[SignalItem]
    candidates: List[CandidateDirection]
    dossiers: Dict[str, Dict]
    scores: List[DirectionScore]
    final_report: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "raw_sources": self.raw_sources,
            "documents": [x.model_dump(mode="json") for x in self.documents],
            "signals": [x.model_dump(mode="json") for x in self.signals],
            "candidates": [x.model_dump(mode="json") for x in self.candidates],
            "dossiers": self.dossiers,
            "scores": [x.model_dump(mode="json") for x in self.scores],
            "final_report": self.final_report,
        }


def run_intelligence_pipeline(topic: str, user_goal: str, raw_sources: List[Dict[str, Any]]) -> PipelineResult:
    registry_items = load_source_registry()
    collected = collect_raw_items(
        topic=topic,
        raw_sources=raw_sources,
        registry_items=registry_items,
        max_sources=settings.max_sources_per_task,
    )
    documents = normalize_documents(collected)
    signals = extract_signals(documents)
    candidates = discover_candidates(signals)
    dossiers = build_direction_dossiers(candidates, documents)
    scores = score_candidates(dossiers)
    final_report = build_markdown_report(
        topic=topic,
        user_goal=user_goal,
        candidates=candidates,
        scores=scores,
        dossiers=dossiers,
    )
    return PipelineResult(
        raw_sources=collected,
        documents=documents,
        signals=signals,
        candidates=candidates,
        dossiers=dossiers,
        scores=scores,
        final_report=final_report,
    )


def stream_report_events(topic: str, user_goal: str, raw_sources: List[Dict[str, Any]]) -> Generator[Dict[str, Any], None, PipelineResult]:
    yield {"phase": "source_registry", "message": "loading source registry"}
    registry_items = load_source_registry()

    yield {"phase": "collector", "message": "collecting raw sources"}
    collected = collect_raw_items(
        topic=topic,
        raw_sources=raw_sources,
        registry_items=registry_items,
        max_sources=settings.max_sources_per_task,
    )
    yield {"phase": "collector", "raw_source_count": len(collected)}

    yield {"phase": "parser_normalizer", "message": "normalizing documents"}
    documents = normalize_documents(collected)
    yield {"phase": "parser_normalizer", "document_count": len(documents)}

    yield {"phase": "signal_extractor", "message": "extracting signals"}
    signals = extract_signals(documents)
    yield {"phase": "signal_extractor", "signal_count": len(signals)}

    yield {"phase": "candidate_discovery", "message": "discovering candidate directions"}
    candidates = discover_candidates(signals)
    yield {"phase": "candidate_discovery", "candidate_count": len(candidates)}

    yield {"phase": "evidence_builder", "message": "building dossiers"}
    dossiers = build_direction_dossiers(candidates, documents)

    yield {"phase": "scoring_engine", "message": "scoring candidates"}
    scores = score_candidates(dossiers)

    yield {"phase": "report_agent", "message": "generating markdown report"}
    final_report = build_markdown_report(
        topic=topic,
        user_goal=user_goal,
        candidates=candidates,
        scores=scores,
        dossiers=dossiers,
    )

    result = PipelineResult(
        raw_sources=collected,
        documents=documents,
        signals=signals,
        candidates=candidates,
        dossiers=dossiers,
        scores=scores,
        final_report=final_report,
    )
    yield {"phase": "done", "message": "report ready"}
    return result

