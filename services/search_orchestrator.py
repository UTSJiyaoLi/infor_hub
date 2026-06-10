from __future__ import annotations

import os
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from services.web_fetcher import (
    detect_source_type,
    fetch_webpage_text,
    unique_by_url,
    utc_now_iso,
)


class SearchBackend(ABC):
    """Abstract search backend."""

    @abstractmethod
    def search(self, query: str, max_results: int, **kwargs: Any) -> List[Dict[str, Any]]:
        """Return list of results, each with at least title, url, content."""
        ...


class TavilyBackend(SearchBackend):
    def __init__(self, api_key: Optional[str] = None):
        from tavily import TavilyClient  # type: ignore[import-untyped]

        key = api_key or os.environ.get("TAVILY_API_KEY")
        if not key:
            raise RuntimeError("Tavily API key is required. Set TAVILY_API_KEY env var.")
        self.client = TavilyClient(api_key=key)

    def search(self, query: str, max_results: int, **kwargs: Any) -> List[Dict[str, Any]]:
        include_domains = kwargs.get("include_domains")
        time_range = kwargs.get("time_range")
        search_kwargs: Dict[str, Any] = {
            "query": query,
            "max_results": max_results,
        }
        if include_domains:
            search_kwargs["include_domains"] = include_domains
        if time_range:
            search_kwargs["time_range"] = time_range
        try:
            result = self.client.search(**search_kwargs)
        except TypeError:
            # Older client versions may not support include_domains.
            search_kwargs.pop("include_domains", None)
            result = self.client.search(**search_kwargs)
        return result.get("results", [])


class DuckDuckGoBackend(SearchBackend):
    def __init__(self) -> None:
        try:
            from ddgs import DDGS  # type: ignore[import-untyped]
        except Exception:
            from duckduckgo_search import DDGS  # type: ignore[import-untyped]
        self._ddgs_cls = DDGS

    def search(self, query: str, max_results: int, **kwargs: Any) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        with self._ddgs_cls() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                out.append(
                    {
                        "title": r.get("title") or "",
                        "url": r.get("href") or r.get("url") or "",
                        "content": r.get("body") or r.get("snippet") or "",
                    }
                )
        return out


class SearxNgBackend(SearchBackend):
    def __init__(self, base_url: Optional[str] = None):
        self.base_url = (
            base_url or os.environ.get("SEARXNG_URL", "http://127.0.0.1:8080")
        ).rstrip("/")

    def search(self, query: str, max_results: int, **kwargs: Any) -> List[Dict[str, Any]]:
        import requests

        params: Dict[str, Any] = {
            "q": query,
            "format": "json",
            "language": "zh-CN",
            "safesearch": 0,
        }
        engines = kwargs.get("engines")
        if engines:
            params["engines"] = engines
        resp = requests.get(
            f"{self.base_url}/search",
            params=params,
            headers={"User-Agent": "infor-hub-collector/0.1"},
            timeout=20,
        )
        resp.raise_for_status()
        rows = resp.json().get("results", [])[:max_results]
        return [
            {
                "title": r.get("title") or "",
                "url": r.get("url") or "",
                "content": r.get("content") or "",
            }
            for r in rows
        ]


class SearchOrchestrator:
    """Unified search + fetch orchestrator."""

    def __init__(
        self,
        backend: SearchBackend,
        include_domains: Optional[List[str]] = None,
        fetch_timeout: float = 20.0,
        max_page_chars: int = 22000,
    ):
        self.backend = backend
        self.include_domains = [d.lower().strip() for d in (include_domains or []) if d.strip()]
        self.fetch_timeout = fetch_timeout
        self.max_page_chars = max_page_chars

    def _host_matches(self, url: str) -> bool:
        if not self.include_domains:
            return True
        host = (urlparse(url).netloc or "").lower()
        return any(host == d or host.endswith("." + d) for d in self.include_domains)

    def _build_time_range(self, time_window_days: Optional[int]) -> Optional[str]:
        """Map days to Tavily time_range values."""
        if time_window_days is None:
            return None
        if time_window_days <= 7:
            return "week"
        if time_window_days <= 30:
            return "month"
        if time_window_days <= 365:
            return "year"
        return None  # Tavily does not support arbitrary long ranges

    def search_and_fetch(
        self,
        query: str,
        max_results: int = 10,
        time_window_days: Optional[int] = None,
        min_text_chars: int = 300,
    ) -> List[Dict[str, Any]]:
        """
        Search using the configured backend, dedupe, filter by domain,
        fetch full text, and normalize into raw-source rows.
        """
        time_range = self._build_time_range(time_window_days)

        search_results = self.backend.search(
            query=query,
            max_results=max_results,
            include_domains=self.include_domains or None,
            time_range=time_range,
        )

        # Deduplicate by URL
        search_results = unique_by_url(search_results)

        # Domain filter
        if self.include_domains:
            search_results = [r for r in search_results if self._host_matches(r.get("url", ""))]

        # Fetch full text for each result
        out_rows: List[Dict[str, Any]] = []
        for r in search_results:
            url = (r.get("url") or "").strip()
            if not url:
                continue

            fetched_text = ""
            try:
                fetched_text = fetch_webpage_text(
                    url=url,
                    timeout=self.fetch_timeout,
                    max_chars=self.max_page_chars,
                )
            except Exception:
                pass  # fallback to snippet only

            snippet = (r.get("content") or "").strip()
            text = "\n\n".join(block for block in [snippet, fetched_text] if block)

            if len(text) < min_text_chars:
                continue

            out_rows.append(
                {
                    "id": f"src_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}",
                    "title": r.get("title") or url or query,
                    "url": url,
                    "source_type": detect_source_type(url),
                    "collected_at": utc_now_iso(),
                    "text": text,
                }
            )

        return out_rows


def create_search_orchestrator(
    backend_name: Optional[str] = None,
    api_key: Optional[str] = None,
    searxng_url: Optional[str] = None,
    include_domains: Optional[List[str]] = None,
) -> SearchOrchestrator:
    """Factory to create a SearchOrchestrator from env/config."""
    name = (backend_name or os.environ.get("SEARCH_BACKEND", "ddgs")).lower()
    if name == "tavily":
        backend: SearchBackend = TavilyBackend(api_key=api_key)
    elif name == "searxng":
        backend = SearxNgBackend(base_url=searxng_url)
    else:
        backend = DuckDuckGoBackend()
    return SearchOrchestrator(backend=backend, include_domains=include_domains)
