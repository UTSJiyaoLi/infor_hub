from __future__ import annotations

from typing import Dict, List

from schemas.pipeline import NormalizedDocument, SignalItem


RULES: Dict[str, List[str]] = {
    "maturity": ["concept", "prototype", "demonstration", "commercial", "量产", "示范", "并网", "海试"],
    "funding_support": ["funding", "grant", "tender", "bid", "融资", "资助", "招标", "合作"],
    "cost_engineering": ["lcoe", "modular", "maintenance", "batch manufacturing", "运维", "模块化", "批量制造"],
    "synergy": ["wind-solar-hydrogen-storage", "energy island", "marine ranch", "风光氢储", "能源岛", "海洋牧场"],
    "standard_certification": ["dnv", "aip", "certification", "standard", "认证", "标准"],
}


def extract_signals(docs: List[NormalizedDocument]) -> List[SignalItem]:
    signals: List[SignalItem] = []
    for doc in docs:
        text = doc.body_markdown.lower()
        for signal_type, keywords in RULES.items():
            for kw in keywords:
                if kw.lower() not in text:
                    continue
                idx = text.find(kw.lower())
                start = max(0, idx - 80)
                end = min(len(text), idx + 120)
                snippet = doc.body_markdown[start:end]
                signals.append(
                    SignalItem(
                        signal_type=signal_type,
                        value=kw,
                        strength=2 if signal_type in {"maturity", "funding_support"} else 1,
                        evidence_doc_id=doc.doc_id,
                        evidence_snippet=snippet,
                    )
                )
                break
    return signals

