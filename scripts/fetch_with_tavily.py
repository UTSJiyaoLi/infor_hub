#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional
from urllib.parse import urlparse

import requests
from tavily import TavilyClient


DEFAULT_INCLUDE_DOMAINS = [
    "arxiv.org",
    "iea.org",
    "nrel.gov",
    "irena.org",
    "iea-oes.org",
    "emec.org.uk",
    "energy.gov",
]

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


def fetch_webpage_text(url: str, timeout: float = 20.0, max_chars: int = 22000) -> str:
    headers = {"User-Agent": USER_AGENT}
    resp = requests.get(url, headers=headers, timeout=timeout)
    resp.raise_for_status()

    content_type = (resp.headers.get("content-type") or "").lower()
    text: str

    if "text/html" in content_type:
        try:
            from bs4 import BeautifulSoup  # type: ignore

            soup = BeautifulSoup(resp.text, "html.parser")
            for tag in soup(["script", "style", "noscript"]):
                tag.decompose()
            text = "\n".join(line.strip() for line in soup.get_text("\n").splitlines() if line.strip())
        except Exception:
            # Fallback if bs4 is unavailable.
            text = re.sub(r"<[^>]+>", " ", resp.text)
            text = compact_ws(text)
    else:
        text = resp.text

    return text[:max_chars]


def try_tavily_search(
    client: TavilyClient,
    query: str,
    max_results: int,
    topic: str,
    include_domains: Optional[List[str]],
) -> Dict[str, Any]:
    kwargs: Dict[str, Any] = {
        "query": query,
        "max_results": max_results,
        "topic": topic,
    }
    if include_domains:
        kwargs["include_domains"] = include_domains

    try:
        return client.search(**kwargs)
    except TypeError:
        # Older client versions may not support include_domains.
        kwargs.pop("include_domains", None)
        return client.search(**kwargs)


def normalize_result(
    result: Dict[str, Any],
    fetched_text: str,
    fallback_query: str,
) -> Dict[str, Any]:
    url = result.get("url") or ""
    title = result.get("title") or url or fallback_query
    snippet = result.get("content") or ""

    text_blocks = [
        snippet.strip(),
        fetched_text.strip(),
    ]
    text = "\n\n".join(block for block in text_blocks if block)

    return {
        "id": f"src_{datetime.now().strftime('%Y%m%d%H%M%S%f')}",
        "title": title,
        "url": url,
        "source_type": detect_source_type(url),
        "collected_at": utc_now_iso(),
        "text": text,
    }


def parse_domains(raw: str) -> List[str]:
    if not raw.strip():
        return []
    return [d.strip() for d in raw.split(",") if d.strip()]


def write_jsonl(path: Path, rows: Iterable[Dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Search high-confidence web sources with Tavily and fetch full page text. "
            "Output is compatible with run_collector(raw_sources=[...])."
        )
    )
    parser.add_argument("--query", required=True, help="Research query")
    parser.add_argument("--topic", default="general", choices=["general", "news", "finance"])
    parser.add_argument("--max-results", type=int, default=8)
    parser.add_argument(
        "--include-domains",
        default=",".join(DEFAULT_INCLUDE_DOMAINS),
        help="Comma-separated domain whitelist for high-reliability sources",
    )
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--min-text-chars", type=int, default=300)
    parser.add_argument("--output", default="data/raw_sources_tavily.jsonl")
    parser.add_argument("--output-json", default="data/raw_sources_tavily.json")
    args = parser.parse_args()

    api_key = os.environ.get("TAVILY_API_KEY")
    if not api_key:
        print("ERROR: TAVILY_API_KEY is not set", file=sys.stderr)
        return 2

    include_domains = parse_domains(args.include_domains)
    client = TavilyClient(api_key=api_key)

    search = try_tavily_search(
        client=client,
        query=args.query,
        max_results=args.max_results,
        topic=args.topic,
        include_domains=include_domains,
    )

    raw_results = search.get("results", [])
    out_rows: List[Dict[str, Any]] = []

    for idx, r in enumerate(raw_results):
        url = (r.get("url") or "").strip()
        if not url:
            continue

        try:
            fetched_text = fetch_webpage_text(url=url, timeout=args.timeout)
            row = normalize_result(r, fetched_text, fallback_query=args.query)
            if len(row["text"]) < args.min_text_chars:
                continue
            out_rows.append(row)
            print(f"[{idx+1}/{len(raw_results)}] OK {url}")
        except Exception as exc:
            print(f"[{idx+1}/{len(raw_results)}] FAIL {url} :: {exc}", file=sys.stderr)

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    write_jsonl(out_path, out_rows)

    out_json = Path(args.output_json)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(out_rows, ensure_ascii=False, indent=2), encoding="utf-8")

    summary = {
        "query": args.query,
        "topic": args.topic,
        "requested": args.max_results,
        "collected": len(out_rows),
        "output_jsonl": str(out_path),
        "output_json": str(out_json),
        "include_domains": include_domains,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
