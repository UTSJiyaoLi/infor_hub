from __future__ import annotations

from typing import Dict, List

from schemas.pipeline import DirectionScore


def _clip_0_20(v: int) -> int:
    return max(0, min(20, v))


def score_candidates(dossiers: Dict[str, Dict]) -> List[DirectionScore]:
    rows: List[DirectionScore] = []
    for cid, ds in dossiers.items():
        candidate = ds.get("candidate", {})
        tags = list(candidate.get("entity_tags") or [])
        doc_count = int(ds.get("doc_count") or 0)
        source_count = len(ds.get("sources") or [])

        growth = _clip_0_20(8 + doc_count * 2)
        feasibility = _clip_0_20(6 + (4 if "maturity" in tags else 0) + min(8, source_count))
        synergy = _clip_0_20(6 + (6 if "synergy" in tags else 1) + min(6, len(tags)))
        moat = _clip_0_20(5 + (8 if "standard_certification" in tags else 0) + min(7, source_count))
        timing = _clip_0_20(7 + (6 if "funding_support" in tags else 0) + min(5, doc_count))

        total = growth + feasibility + synergy + moat + timing
        rationale = [
            f"证据文档数={doc_count}",
            f"来源数量={source_count}",
            f"信号标签={','.join(tags) if tags else 'none'}",
        ]
        rows.append(
            DirectionScore(
                candidate_id=cid,
                growth=growth,
                feasibility=feasibility,
                synergy=synergy,
                moat=moat,
                timing=timing,
                total=total,
                rationale=rationale,
            )
        )
    rows.sort(key=lambda x: x.total, reverse=True)
    return rows

