from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import requests

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def compact_ws(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def detect_source_type(url: str) -> str:
    host = (urlparse(url).netloc or "").lower()
    if "arxiv.org" in host:
        return "paper"
    if host.endswith(".gov") or host.endswith(".edu"):
        return "official"
    if any(x in host for x in ["iea.org", "irena.org", "iea-oes.org", "emec.org.uk"]):
        return "official"
    return "web"


def fetch_webpage_text(
    url: str,
    timeout: float = 20.0,
    max_chars: int = 22000,
    headers: Optional[Dict[str, str]] = None,
) -> str:
    """Fetch a URL and return clean plain text."""
    _headers = {"User-Agent": USER_AGENT}
    if headers:
        _headers.update(headers)

    resp = requests.get(url, headers=_headers, timeout=timeout)
    resp.raise_for_status()

    content_type = (resp.headers.get("content-type") or "").lower()
    text: str

    if "text/html" in content_type:
        try:
            from bs4 import BeautifulSoup  # type: ignore[import-untyped]

            soup = BeautifulSoup(resp.text, "html.parser")
            for tag in soup(["script", "style", "noscript"]):
                tag.decompose()
            text = "\n".join(
                line.strip()
                for line in soup.get_text("\n").splitlines()
                if line.strip()
            )
        except Exception:
            text = re.sub(r"<[^>]+>", " ", resp.text)
            text = compact_ws(text)
    else:
        text = resp.text

    return text[:max_chars]


def unique_by_url(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen: set[str] = set()
    out: List[Dict[str, Any]] = []
    for r in rows:
        u = (r.get("url") or "").strip()
        if not u or u in seen:
            continue
        seen.add(u)
        out.append(r)
    return out
