from __future__ import annotations


def test_pipeline_v3_module_exists():
    from services import pipeline_v3

    assert callable(pipeline_v3.run_intelligence_pipeline_v3)
    assert callable(pipeline_v3.stream_report_events_v3)


def test_report_builder_module_exists():
    from services import report_builder

    assert hasattr(report_builder, "ReportBuilder")


def test_content_analyzer_module_exists():
    from services import content_analyzer

    assert hasattr(content_analyzer, "ContentAnalyzer")


def test_intelligence_synthesizer_module_exists():
    from services import intelligence_synthesizer

    assert hasattr(intelligence_synthesizer, "IntelligenceSynthesizer")


def test_search_orchestrator_module_exists():
    from services import search_orchestrator

    assert hasattr(search_orchestrator, "SearchOrchestrator")
    assert hasattr(search_orchestrator, "create_search_orchestrator")
