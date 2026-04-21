from __future__ import annotations

from collections import defaultdict
from hashlib import md5
from typing import Dict, List

from schemas.pipeline import CandidateDirection, SignalItem


KEYWORD_TO_CANDIDATE = {
    "concrete": "混凝土浮式基础",
    "floating": "混凝土浮式基础",
    "hydrogen": "海上风电制氢平台",
    "wave": "近岸波浪能与防波堤一体化",
    "tidal": "潮流能海岛独立供能",
    "energy island": "海上能源岛基础设施",
    "maintenance": "新型安装运维装备",
}


def discover_candidates(signals: List[SignalItem]) -> List[CandidateDirection]:
    buckets: Dict[str, List[SignalItem]] = defaultdict(list)
    for sig in signals:
        token = sig.value.lower()
        name = None
        for kw, candidate in KEYWORD_TO_CANDIDATE.items():
            if kw in token:
                name = candidate
                break
        if not name:
            if sig.signal_type == "maturity":
                name = "新型海洋能源技术方向"
            else:
                name = "综合能源协同方向"
        buckets[name].append(sig)

    outputs: List[CandidateDirection] = []
    for name, items in buckets.items():
        cid = md5(name.encode("utf-8")).hexdigest()[:10]
        doc_ids = sorted({i.evidence_doc_id for i in items})
        signal_types = sorted({i.signal_type for i in items})
        outputs.append(
            CandidateDirection(
                candidate_id=cid,
                name=name,
                description=f"{name}（由近期信号自动聚合）",
                entity_tags=signal_types,
                representative_evidence=items[:5],
                related_doc_ids=doc_ids,
            )
        )
    return outputs

