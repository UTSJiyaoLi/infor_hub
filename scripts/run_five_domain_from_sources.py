#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from graph import run_collector
from langchain.chat_models import init_chat_model
from tools import parse_json


def slugify(text: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_-]+", "_", text.strip().lower())
    return cleaned.strip("_")[:80] or "domain"


def rank_domains_with_llm(domain_results: List[Dict[str, Any]], focus: str) -> Dict[str, Any]:
    model_name = os.environ.get("COLLECTOR_MODEL", "openai:gpt-4o")
    model = init_chat_model(model_name)

    compact: List[Dict[str, Any]] = []
    for item in domain_results:
        result = item.get("result", {})
        trend = result.get("trend_analysis")
        comparison = result.get("comparison")
        compact.append(
            {
                "domain": item["domain"],
                "sources_count": item.get("sources_count", 0),
                "final_report_excerpt": (result.get("final_report", "") or "")[:2800],
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
        + json.dumps(compact, ensure_ascii=False, indent=2)
    )

    raw = model.invoke(prompt)
    content = raw.content if hasattr(raw, "content") else str(raw)
    if isinstance(content, list):
        text = "\n".join(x.get("text", "") if isinstance(x, dict) else str(x) for x in content)
    else:
        text = str(content)
    parsed = parse_json(text)
    if isinstance(parsed, dict):
        return parsed
    if isinstance(parsed, list):
        ranked_domains = []
        for item in parsed:
            if isinstance(item, dict):
                ranked_domains.append(item)
        best = ranked_domains[0]["domain"] if ranked_domains and isinstance(ranked_domains[0], dict) and ranked_domains[0].get("domain") else ""
        return {
            "ranked_domains": ranked_domains,
            "recommended_domain": best,
            "recommendation_summary": "Ranking parsed from list output.",
            "detailed_report_md": "",
        }
    return {
        "ranked_domains": [],
        "recommended_domain": "",
        "recommendation_summary": "Ranking output parse fallback.",
        "detailed_report_md": "",
    }


def load_manifest(path: Path) -> List[Dict[str, str]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("manifest must be a JSON list")
    rows: List[Dict[str, str]] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        domain = str(item.get("domain", "")).strip()
        sources_file = str(item.get("sources_file", "")).strip()
        if domain and sources_file:
            rows.append({"domain": domain, "sources_file": sources_file})
    if not rows:
        raise ValueError("manifest has no valid domain/sources_file entries")
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Run 5-domain pipeline from pre-fetched raw sources JSON files.")
    parser.add_argument("--manifest", required=True, help="JSON list: [{domain, sources_file}]")
    parser.add_argument("--focus", default="identify the most promising domain with best growth headroom")
    parser.add_argument("--output-root", default="outputs/five_domain_pipeline_from_sources")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    output_root = repo_root / args.output_root / datetime.now().strftime("%Y%m%d_%H%M%S")
    output_root.mkdir(parents=True, exist_ok=True)

    rows = load_manifest(Path(args.manifest))
    domain_runs: List[Dict[str, Any]] = []
    errors: List[Dict[str, str]] = []

    for row in rows:
        domain = row["domain"]
        src_file = Path(row["sources_file"])
        domain_dir = output_root / slugify(domain)
        domain_dir.mkdir(parents=True, exist_ok=True)
        try:
            raw_sources = json.loads(src_file.read_text(encoding="utf-8"))
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
        "domains_requested": [r["domain"] for r in rows],
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
