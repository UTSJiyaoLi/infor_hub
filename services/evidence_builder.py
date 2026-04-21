from __future__ import annotations

from typing import Dict, List

from schemas.pipeline import CandidateDirection, NormalizedDocument


def build_direction_dossiers(
    candidates: List[CandidateDirection], docs: List[NormalizedDocument]
) -> Dict[str, Dict]:
    by_id = {d.doc_id: d for d in docs}
    dossier: Dict[str, Dict] = {}
    for candidate in candidates:
        evidence_docs = [by_id[x] for x in candidate.related_doc_ids if x in by_id]
        unique_urls = sorted({d.url for d in evidence_docs if d.url})
        dossier[candidate.candidate_id] = {
            "candidate": candidate.model_dump(mode="json"),
            "doc_count": len(evidence_docs),
            "sources": unique_urls,
            "evidence_titles": [d.title for d in evidence_docs[:8]],
        }
    return dossier

