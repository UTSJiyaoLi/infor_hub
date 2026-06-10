from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from langchain.chat_models import init_chat_model  # type: ignore[import-untyped]

from schemas.technology import TechnologyProfile
from tools import parse_json


class ContentAnalyzer:
    """Use LLM to extract structured TechnologyProfile from raw article text."""

    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name or os.environ.get(
            "COLLECTOR_MODEL", "openai:gpt-4o"
        )
        self.model = init_chat_model(self.model_name)

    def _build_prompt(self, title: str, url: str, text: str, topic: str) -> str:
        # Truncate text to keep prompt size reasonable
        safe_text = text[:12000]
        return (
            "You are an intelligence extraction specialist for offshore renewable energy "
            "and marine engineering technologies.\n\n"
            f"Research topic: {topic}\n"
            f"Article title: {title}\n"
            f"URL: {url}\n\n"
            "Article text:\n"
            "---\n"
            f"{safe_text}\n"
            "---\n\n"
            "Instructions:\n"
            "1. Determine whether this article describes a concrete technology, device, "
            "project, platform, or company related to the research topic.\n"
            "2. If it does NOT contain such content, return ONLY:\n"
            '   {"name": "UNRELATED"}\n'
            "3. If it DOES contain relevant content, extract a TechnologyProfile with as "
            "many fields filled as the text supports. Do NOT hallucinate unsupported facts.\n"
            "4. For engineering parameters, include concrete values with units (e.g. '15 MW', '35 m depth').\n"
            "5. For timeline, list key milestones with dates when mentioned.\n"
            "6. Include this article as a SourceReference in the sources list.\n"
            "7. Preserve uncertainty: if a claim is tentative, note it in uncertainty_note.\n\n"
            "Return valid JSON matching the TechnologyProfile schema."
        )

    def analyze(
        self, title: str, url: str, text: str, topic: str
    ) -> Optional[TechnologyProfile]:
        prompt = self._build_prompt(title, url, text, topic)

        # Attempt 1: structured output via LangChain
        try:
            structured = self.model.with_structured_output(TechnologyProfile)
            result = structured.invoke(prompt)
            if isinstance(result, TechnologyProfile):
                if result.name.strip().upper() == "UNRELATED":
                    return None
                return result
        except Exception:
            pass

        # Attempt 2: plain invoke + manual JSON parse
        try:
            raw = self.model.invoke(prompt)
            content = raw.content if hasattr(raw, "content") else str(raw)
            parsed = parse_json(content)
            if not isinstance(parsed, dict):
                return None
            if parsed.get("name", "").strip().upper() == "UNRELATED":
                return None
            return TechnologyProfile.model_validate(parsed)
        except Exception:
            return None

    def analyze_batch(
        self, documents: List[Dict[str, Any]], topic: str
    ) -> List[TechnologyProfile]:
        """Analyze a batch of documents, skipping unparseable or unrelated ones."""
        profiles: List[TechnologyProfile] = []
        for doc in documents:
            profile = self.analyze(
                title=str(doc.get("title", "")),
                url=str(doc.get("url", "")),
                text=str(doc.get("text", "")),
                topic=topic,
            )
            if profile is not None:
                profiles.append(profile)
        return profiles
