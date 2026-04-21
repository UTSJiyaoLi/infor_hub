from __future__ import annotations

from typing import Dict, List

from schemas.pipeline import CandidateDirection, DirectionScore


def build_markdown_report(
    *,
    topic: str,
    user_goal: str,
    candidates: List[CandidateDirection],
    scores: List[DirectionScore],
    dossiers: Dict[str, Dict],
) -> str:
    score_map = {s.candidate_id: s for s in scores}
    lines: List[str] = [
        f"# Infor Hub 情报报告：{topic}",
        "",
        "## 本期扫描范围",
        f"- 主题：{topic}",
        f"- 目标：{user_goal or '未提供'}",
        f"- 候选方向数：{len(candidates)}",
        "",
        "## 本期优先关注方向",
    ]

    for rank, sc in enumerate(scores[:10], start=1):
        cinfo = dossiers.get(sc.candidate_id, {}).get("candidate", {})
        cname = cinfo.get("name", sc.candidate_id)
        lines.append(f"{rank}. **{cname}**（总分 {sc.total}/100）")

    lines.append("")
    lines.append("## 方向详情")
    for sc in scores:
        c = dossiers.get(sc.candidate_id, {}).get("candidate", {})
        name = c.get("name", sc.candidate_id)
        desc = c.get("description", "")
        tags = c.get("entity_tags", [])
        titles = dossiers.get(sc.candidate_id, {}).get("evidence_titles", [])
        lines.extend(
            [
                f"### {name}",
                f"- 核心判断：{desc}",
                f"- 阶段标签：{', '.join(tags) if tags else '未识别'}",
                f"- 评分：Growth {sc.growth} / Feasibility {sc.feasibility} / Synergy {sc.synergy} / Moat {sc.moat} / Timing {sc.timing}",
                f"- 关键证据：{'; '.join(titles[:3]) if titles else '暂无'}",
                f"- 评分依据：{' | '.join(sc.rationale)}",
                "",
            ]
        )

    lines.extend(
        [
            "## 横向比较结论",
            "- 优先投入证据丰富且具备成熟度/标准化信号的方向。",
            "- 对信号强但证据薄的方向，建议下一轮重点补证。",
            "",
        ]
    )
    return "\n".join(lines)

