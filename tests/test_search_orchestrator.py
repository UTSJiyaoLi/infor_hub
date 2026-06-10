from __future__ import annotations

import pytest

from services.search_orchestrator import SearchOrchestrator


def test_host_matches_no_domains():
    orch = SearchOrchestrator(backend=None, include_domains=[])
    assert orch._host_matches("http://anything.com") is True


def test_host_matches_with_domains():
    orch = SearchOrchestrator(backend=None, include_domains=["example.com"])
    assert orch._host_matches("http://example.com/page") is True
    assert orch._host_matches("http://sub.example.com/page") is True
    assert orch._host_matches("http://other.com") is False


def test_build_time_range():
    orch = SearchOrchestrator(backend=None)
    assert orch._build_time_range(5) == "week"
    assert orch._build_time_range(14) == "week"
    assert orch._build_time_range(30) == "month"
    assert orch._build_time_range(200) == "year"
    assert orch._build_time_range(None) is None
