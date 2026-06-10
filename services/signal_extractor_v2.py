from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from langchain.chat_models import init_chat_model  # type: ignore[import-untyped]

from schemas.pipeline import EvidenceSignal
from tools import parse_json


class SignalExtractorV2:
    """
    Use LLM to extract structured evidence signals from raw documents.
    Each signal maps to one of the six scoring dimensions.
    """

    DIMENSIONS = {
        "maturity": "技术成熟度：海试、并网、量产、TRL提升、示范运行、商业化运营",
        "market": "市场与政策：招标公告、大额订单、政府补贴、政策文件、国际合作",
        "moat": "技术壁垒：专利申请、标准认证(DNV/AiP)、独家技术、核心部件自研",
        "scalability": "规模化潜力：模块化设计、产能扩张计划、可复制部署、阵列化",
        "cost": "成本趋势：LCOE下降、供应链本土化、批量制造、运维成本降低",
        "timing": "时间窗口：近期密集报道、竞品动态、资本进入、产业链配套成熟",
    }

    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name or os.environ.get(
            "COLLECTOR_MODEL", "openai:gpt-4o"
        )
        self.model = init_chat_model(self.model_name)

    def _build_prompt(self, title: str, url: str, text: str, topic: str) -> str:
        dims_text = "\n".join(f"  - {k}: {v}" for k, v in self.DIMENSIONS.items())
        safe_text = text[:8000]
        return (
            "你是一名技术情报信号提取专家。请从以下文章中提取所有与可发展性评估相关的证据信号。\n\n"
            f"研究主题: {topic}\n"
            f"文章标题: {title}\n"
            f"URL: {url}\n\n"
            "文章文本:\n"
            "---\n"
            f"{safe_text}\n"
            "---\n\n"
            "六个评估维度:\n"
            f"{dims_text}\n\n"
            "Instructions:\n"
            "1. 只提取文章中明确提到的具体事实（有日期、数字、机构名称为佳）。\n"
            "2. 不要提取模糊或推测性表述。\n"
            "3. 如果文章与主题无关或没有实质性内容，返回空数组 []。\n"
            "4. 每条信号必须标注 dimension、signal_type、description、strength(1-5)。\n\n"
            "Return strict JSON array:\n"
            '[\n'
            '  {"dimension": "maturity", "signal_type": "sea_trial", "description": "...", "strength": 3}\n'
            ']'
        )

    def extract(
        self, title: str, url: str, text: str, topic: str, doc_id: str = ""
    ) -> List[EvidenceSignal]:
        prompt = self._build_prompt(title, url, text, topic)
        try:
            raw = self.model.invoke(prompt)
            content = raw.content if hasattr(raw, "content") else str(raw)
            parsed = parse_json(content)
            if not isinstance(parsed, list):
                return []
            signals: List[EvidenceSignal] = []
            for row in parsed:
                if not isinstance(row, dict):
                    continue
                dim = str(row.get("dimension", "")).lower().strip()
                if dim not in self.DIMENSIONS:
                    continue
                signals.append(
                    EvidenceSignal(
                        dimension=dim,
                        signal_type=str(row.get("signal_type", "")),
                        description=str(row.get("description", "")),
                        strength=max(1, min(5, int(row.get("strength", 1)))),
                        source_doc_id=doc_id,
                        source_url=url,
                    )
                )
            return signals
        except Exception:
            return []

    def extract_batch(
        self, documents: List[Dict[str, Any]], topic: str
    ) -> List[EvidenceSignal]:
        all_signals: List[EvidenceSignal] = []
        for doc in documents:
            sigs = self.extract(
                title=str(doc.get("title", "")),
                url=str(doc.get("url", "")),
                text=str(doc.get("text", "")),
                topic=topic,
                doc_id=str(doc.get("id", doc.get("url", ""))),
            )
            all_signals.extend(sigs)
        return all_signals
