from __future__ import annotations

import json
from typing import List, Dict

from graph import run_collector


def build_demo_sources() -> List[Dict]:
    """
    构造一个最小可跑的 demo 数据
    （你后面可以替换成真实抓取/解析结果）
    """

    return [
        {
            "title": "Wave energy device - example summary",
            "source_type": "report",
            "url": "https://example.com/wave1",
            "text": """
            CorPower C4 is a point absorber wave energy device.
            It is designed for offshore deployment and can survive extreme storms.
            The system uses phase control to amplify energy capture.
            Demonstration projects are ongoing in Europe.
            """
        },
        {
            "title": "Offshore hydrogen pilot project",
            "source_type": "report",
            "url": "https://example.com/hydrogen1",
            "text": """
            Sealhyfe is a floating offshore hydrogen production system.
            It integrates electrolysis with offshore wind energy.
            The pilot aims to validate continuous hydrogen production at sea.
            The project represents early-stage commercialization.
            """
        }
    ]


def run_demo():
    topic = "offshore renewable energy systems"
    user_goal = "生成类似工程科技动态的情报简报，并包含技术对比和趋势分析"

    raw_sources = build_demo_sources()

    result = run_collector({
        "topic": topic,
        "user_goal": user_goal,
        "raw_sources": raw_sources
    })

    print("\n================ FINAL REPORT ================\n")
    print(result.get("final_report", ""))

    print("\n================ CASE TABLE ================\n")
    print(result.get("case_table", ""))

    print("\n================ LOGS ================\n")
    for log in result.get("logs", []):
        print("-", log)


if __name__ == "__main__":
    run_demo()