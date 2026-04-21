#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from graph import run_collector
from langchain.chat_models import init_chat_model
from tools import parse_json


DEFAULT_DOMAINS = [
    "offshore wind",
    "floating solar",
    "wave energy",
    "tidal energy",
    "offshore hydrogen",
]


def slugify(text: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_-]+", "_", text.strip().lower())
    return cleaned.strip("_")[:80] or "domain"


def ensure_free_search_backend(backend: str) -> None:
    if backend == "ddgs":
        has_ddgs = importlib.util.find_spec("ddgs") is not None
        has_old = importlib.util.find_spec("duckduckgo_search") is not None
        if not (has_ddgs or has_old):
            raise RuntimeError(
                "backend=ddgs requires `ddgs` (or `duckduckgo_search`) in current env. "
                "Please install it in your own env or switch to --backend searxng."
            )


def load_domains(args: argparse.Namespace) -> List[str]:
    if args.domains_file:
        payload = json.loads(Path(args.domains_file).read_text(encoding="utf-8"))
        if not isinstance(payload, list) or not payload:
            raise ValueError("domains_file must be a non-empty JSON list")
        return [str(x).strip() for x in payload if str(x).strip()]
    if args.domains:
        return [x.strip() for x in args.domains.split(",") if x.strip()]
    return DEFAULT_DOMAINS


def build_query(domain: str, focus: str) -> str:
    return f"{domain} latest 2025 2026 engineering commercialization {focus}"


def run_free_fetch(
    repo_root: Path,
    backend: str,
    query: str,
    max_results: int,
    include_domains: str,
    out_json: Path,
    searxng_url: str,
    searxng_engines: str,
) -> None:
    cmd = [
        sys.executable,
        str(repo_root / "scripts" / "fetch_with_free_search.py"),
        "--backend",
        backend,
        "--query",
        query,
        "--max-results",
        str(max_results),
        "--include-domains",
        include_domains,
        "--output-json",
        str(out_json),
        "--output",
        str(out_json.with_suffix(".jsonl")),
    ]
    if backend == "searxng":
        cmd.extend(["--searxng-url", searxng_url])
        if searxng_engines.strip():
            cmd.extend(["--searxng-engines", searxng_engines.strip()])

    p = subprocess.run(cmd, cwd=str(repo_root), capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(
            f"free search failed for query={query}\nSTDOUT:\n{p.stdout}\nSTDERR:\n{p.stderr}"
        )


def summarize_for_ranking(domain_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    compact: List[Dict[str, Any]] = []
    for item in domain_results:
        result = item.get("result", {})
        trend = result.get("trend_analysis")
        comparison = result.get("comparison")
        compact.append(
            {
                "domain": item["domain"],
                "sources_count": item.get("sources_count", 0),
                "final_report_excerpt": (result.get("final_report", "") or "")[:2500],
                "trend_analysis": (
                    trend.model_dump(mode="json") if hasattr(trend, "model_dump") else trend
                ),
                "comparison": (
                    comparison.model_dump(mode="json")
                    if hasattr(comparison, "model_dump")
                    else comparison
                ),
                "gaps_count": len(result.get("gaps", []) or []),
            }
        )
    return compact


def rank_domains_with_llm(domain_results: List[Dict[str, Any]], focus: str) -> Dict[str, Any]:
    model_name = os.environ.get("COLLECTOR_MODEL", "openai:gpt-4o")
    model = init_chat_model(model_name)

    material = summarize_for_ranking(domain_results)
    prompt = (
        "You are an investment and technology strategy analyst.\n"
        "Given 5 domain intelligence summaries, rank them by future potential and development headroom.\n"
        "Decision criteria:\n"
        "1) technical feasibility trajectory\n"
        "2) commercialization momentum\n"
        "3) scalability and deployment constraints\n"
        "4) policy/regulatory support signals\n"
        "5) ecosystem maturity and execution risk\n\n"
        f"User focus: {focus}\n\n"
        "Return strict JSON only with this schema:\n"
        "{\n"
        '  "ranked_domains": [\n'
        '    {"domain": "...", "score_0_100": 0, "reasons": ["..."], "risks": ["..."]}\n'
        "  ],\n"
        '  "recommended_domain": "...",\n'
        '  "recommendation_summary": "...",\n'
        '  "detailed_report_md": "markdown report with evidence-backed rationale and next actions"\n'
        "}\n\n"
        "Input domain material:\n"
        + json.dumps(material, ensure_ascii=False, indent=2)
    )

    raw = model.invoke(prompt)
    content = raw.content if hasattr(raw, "content") else str(raw)
    if isinstance(content, list):
        text = "\n".join(x.get("text", "") if isinstance(x, dict) else str(x) for x in content)
    else:
        text = str(content)
    return parse_json(text)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run full 5-domain pipeline: free search fetch -> per-domain collector -> cross-domain ranking."
    )
    parser.add_argument("--domains", default="", help="Comma-separated domains. Default is built-in 5 domains.")
    parser.add_argument("--domains-file", default="", help="JSON file containing domain list")
    parser.add_argument("--focus", default="identify the most promising domain with best growth headroom")
    parser.add_argument("--backend", choices=["ddgs", "searxng"], default="ddgs")
    parser.add_argument("--searxng-url", default="http://127.0.0.1:8080")
    parser.add_argument("--searxng-engines", default="")
    parser.add_argument("--max-results-per-domain", type=int, default=8)
    parser.add_argument(
        "--include-domains",
        default="arxiv.org,iea.org,nrel.gov,irena.org,iea-oes.org,emec.org.uk,energy.gov",
    )
    parser.add_argument("--output-root", default="outputs/five_domain_pipeline")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    output_root = repo_root / args.output_root / datetime.now().strftime("%Y%m%d_%H%M%S")
    output_root.mkdir(parents=True, exist_ok=True)

    domains = load_domains(args)
    ensure_free_search_backend(args.backend)

    domain_runs: List[Dict[str, Any]] = []
    errors: List[Dict[str, Any]] = []

    for domain in domains:
        domain_dir = output_root / slugify(domain)
        domain_dir.mkdir(parents=True, exist_ok=True)
        sources_json = domain_dir / "raw_sources.json"
        query = build_query(domain, args.focus)

        try:
            run_free_fetch(
                repo_root=repo_root,
                backend=args.backend,
                query=query,
                max_results=args.max_results_per_domain,
                include_domains=args.include_domains,
                out_json=sources_json,
                searxng_url=args.searxng_url,
                searxng_engines=args.searxng_engines,
            )
            raw_sources = json.loads(sources_json.read_text(encoding="utf-8"))
            result = run_collector(
                {
                    "topic": domain,
                    "user_goal": args.focus,
                    "raw_sources": raw_sources,
                }
            )
            (domain_dir / "collector_result.json").write_text(
                json.dumps(result, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
            )
            (domain_dir / "final_report.md").write_text(result.get("final_report", ""), encoding="utf-8")
            domain_runs.append(
                {
                    "domain": domain,
                    "query": query,
                    "sources_count": len(raw_sources),
                    "result": result,
                    "dir": str(domain_dir),
                }
            )
            print(f"[OK] {domain} sources={len(raw_sources)}")
        except Exception as exc:
            errors.append({"domain": domain, "error": str(exc)})
            print(f"[FAIL] {domain} :: {exc}", file=sys.stderr)

    if not domain_runs:
        summary = {"ok": False, "errors": errors, "output_root": str(output_root)}
        (output_root / "pipeline_summary.json").write_text(
            json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 2

    ranking = rank_domains_with_llm(domain_runs, focus=args.focus)
    (output_root / "ranking_result.json").write_text(
        json.dumps(ranking, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (output_root / "ranking_report.md").write_text(
        ranking.get("detailed_report_md", ""), encoding="utf-8"
    )

    summary = {
        "ok": True,
        "domains_requested": domains,
        "domains_completed": [d["domain"] for d in domain_runs],
        "errors": errors,
        "recommended_domain": ranking.get("recommended_domain"),
        "output_root": str(output_root),
    }
    (output_root / "pipeline_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

