from __future__ import annotations

import pytest

from services.web_fetcher import compact_ws, detect_source_type, unique_by_url


def test_compact_ws_collapses_spaces():
    assert compact_ws("hello   world\n\n  foo") == "hello world foo"


def test_detect_source_type_arxiv():
    assert detect_source_type("https://arxiv.org/abs/1234") == "paper"


def test_detect_source_type_gov():
    assert detect_source_type("https://www.nrel.gov/news/") == "official"


def test_detect_source_type_generic():
    assert detect_source_type("https://example.com/article") == "web"


def test_unique_by_url_removes_duplicates():
    rows = [
        {"url": "http://a.com", "title": "A"},
        {"url": "http://b.com", "title": "B"},
        {"url": "http://a.com", "title": "A2"},
    ]
    result = unique_by_url(rows)
    assert len(result) == 2
    assert result[0]["title"] == "A"
    assert result[1]["title"] == "B"
