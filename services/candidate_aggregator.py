from __future__ import annotations

from collections import defaultdict
from hashlib import md5
from typing import Any, Dict, List, Optional

from schemas.pipeline import EvidenceSignal
from schemas.technology import TechnologyProfile


class CandidateAggregator:
    """
    Aggregate TechnologyProfiles and EvidenceSignals into candidate directions.

    Grouping logic:
    1. First try exact match on (tech_route + name)
    2. Then fuzzy match on tech_route alone
    3. Fallback to energy_type
    """

    def aggregate(
        self,
        profiles: List[TechnologyProfile],
        signals: List[EvidenceSignal],
        documents: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Returns list of candidate dicts:
        {
            candidate_id: str,
            name: str,
            tech_route: str,
            energy_type: str,
            profiles: List[TechnologyProfile],
            signals: List[EvidenceSignal],
            documents: List[Dict],
        }
        """
        # Step 1: assign each profile to a bucket key
        buckets: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {
                "profiles": [],
                "signals": [],
                "documents": [],
                "name": "",
                "tech_route": "",
                "energy_type": "",
            }
        )

        for p in profiles:
            key = self._make_key(p)
            buckets[key]["profiles"].append(p)
            buckets[key]["name"] = buckets[key]["name"] or p.name
            buckets[key]["tech_route"] = buckets[key]["tech_route"] or (p.tech_route or "")
            buckets[key]["energy_type"] = buckets[key]["energy_type"] or (p.energy_type or "")

        # Step 2: assign signals to nearest bucket by source_url matching
        url_to_bucket: Dict[str, str] = {}
        for key, bucket in buckets.items():
            for p in bucket["profiles"]:
                for s in p.sources:
                    if s.url:
                        url_to_bucket[s.url] = key

        for sig in signals:
            target_key = None
            # Try match by source_url
            if sig.source_url and sig.source_url in url_to_bucket:
                target_key = url_to_bucket[sig.source_url]
            else:
                # Fallback: match by signal description similarity to bucket names
                target_key = self._find_best_bucket(sig, buckets)
            if target_key:
                buckets[target_key]["signals"].append(sig)

        # Step 3: assign documents to buckets by URL matching
        doc_url_to_bucket = url_to_bucket
        for doc in documents:
            url = str(doc.get("url", ""))
            if url and url in doc_url_to_bucket:
                buckets[doc_url_to_bucket[url]]["documents"].append(doc)

        # Step 4: build output candidates
        candidates: List[Dict[str, Any]] = []
        for key, bucket in buckets.items():
            if not bucket["profiles"] and not bucket["signals"]:
                continue
            cid = md5(key.encode("utf-8")).hexdigest()[:10]
            candidates.append(
                {
                    "candidate_id": cid,
                    "name": bucket["name"] or key,
                    "tech_route": bucket["tech_route"],
                    "energy_type": bucket["energy_type"],
                    "profiles": bucket["profiles"],
                    "signals": bucket["signals"],
                    "documents": bucket["documents"],
                }
            )

        # Sort by total signal strength descending (preliminary)
        candidates.sort(
            key=lambda x: sum(s.strength for s in x["signals"]), reverse=True
        )
        return candidates

    def _make_key(self, p: TechnologyProfile) -> str:
        route = (p.tech_route or "").strip().lower()
        name = (p.name or "").strip().lower()
        energy = (p.energy_type or "").strip().lower()
        if route and name:
            return f"{route}::{name}"
        if route:
            return route
        if energy:
            return energy
        return name or "unknown"

    def _find_best_bucket(
        self, sig: EvidenceSignal, buckets: Dict[str, Dict[str, Any]]
    ) -> Optional[str]:
        """Find bucket whose name/tech_route most closely matches signal description."""
        desc = sig.description.lower()
        best_key = None
        best_score = 0
        for key, bucket in buckets.items():
            score = 0
            name = (bucket["name"] or "").lower()
            tech = (bucket["tech_route"] or "").lower()
            if name and name in desc:
                score += 3
            if tech and tech in desc:
                score += 2
            if score > best_score:
                best_score = score
                best_key = key
        return best_key
