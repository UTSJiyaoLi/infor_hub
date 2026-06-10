from __future__ import annotations

from typing import Any, Dict, List

from schemas.pipeline import (
    EvaluatedCandidate,
    RankingResult,
)
from schemas.technology import (
    ComparisonResult,
    IntelligenceReportPackage,
    TrendAnalysis,
    TechnologyProfile,
)


class ReportBuilder:
    """Render intelligence packages / ranking results into markdown briefings."""

    # ------------------------------------------------------------------ #
    # Generic package report (legacy / full comparison mode)
    # ------------------------------------------------------------------ #

    def build(self, package: IntelligenceReportPackage, user_goal: str = "") -> str:
        lines: List[str] = []
        lines.append(f"# {package.topic} — 技术情报简报")
        lines.append("")
        if user_goal:
            lines.append(f"**分析目标**: {user_goal}")
        lines.append(f"**收录案例数**: {len(package.cases)}")
        lines.append("")

        lines.extend(self._section_overview(package))
        lines.extend(self._section_background(package))
        lines.extend(self._section_cases(package))
        lines.extend(self._section_comparison(package))
        lines.extend(self._section_trends(package))
        lines.extend(self._section_editorial(package))
        lines.extend(self._section_gaps(package))
        lines.extend(self._section_sources(package))

        return "\n".join(lines)

    # ------------------------------------------------------------------ #
    # Top-1 deep report (TIDE algorithm output)
    # ------------------------------------------------------------------ #

    def build_top1_report(self, ranking: RankingResult, user_goal: str = "") -> str:
        """Generate a report focused on the top-ranked candidate."""
        lines: List[str] = []
        top = ranking.top_candidate
        all_candidates = ranking.candidates

        # Header
        lines.append(f"# {all_candidates[0].name if all_candidates else '情报分析'} — 技术可发展性评估报告")
        lines.append("")
        if user_goal:
            lines.append(f"**分析目标**: {user_goal}")
        lines.append(f"**评估候选方向数**: {len(all_candidates)}")
        lines.append("")

        # 1. Executive Summary
        lines.extend(self._top1_executive_summary(top, all_candidates))

        # 2. Full Ranking Table
        lines.extend(self._top1_ranking_table(all_candidates, ranking.weights))

        # 3. Top 1 Deep Dive
        if top:
            lines.extend(self._top1_deep_dive(top))
        else:
            lines.append("## 3. 最优候选深度分析")
            lines.append("未找到满足门槛条件的候选方向。建议放宽搜索条件或扩大时间窗口。")
            lines.append("")

        # 4. Risk & Uncertainty
        lines.extend(self._top1_risk_analysis(top))

        # 5. Recommendations
        lines.extend(self._top1_recommendations(top))

        # 6. Sources
        lines.extend(self._top1_sources(top))

        return "\n".join(lines)

    # ------------------------------------------------------------------ #
    # Top-1 section helpers
    # ------------------------------------------------------------------ #

    def _top1_executive_summary(
        self, top: EvaluatedCandidate | None, all_candidates: List[EvaluatedCandidate]
    ) -> List[str]:
        lines: List[str] = ["## 1. 执行摘要", ""]
        if not top:
            lines.append("本期评估未发现满足门槛条件（总分≥60，独立来源≥2）的候选方向。")
            lines.append("")
            return lines

        lines.append(
            f"经过对 {len(all_candidates)} 个候选方向的六维度评估，"
            f"**{top.name}** 以 **{top.total_score} 分** 排名第一，"
            f"被推荐为最具可发展性的技术方向。"
        )
        lines.append("")
        lines.append("**核心优势维度**:")
        ds = top.dimension_scores
        dims = [
            ("技术成熟度", ds.maturity),
            ("市场与政策", ds.market),
            ("技术壁垒", ds.moat),
            ("规模化潜力", ds.scalability),
            ("成本趋势", ds.cost),
            ("时间窗口", ds.timing),
        ]
        dims.sort(key=lambda x: x[1], reverse=True)
        for name, score in dims[:3]:
            lines.append(f"- {name}: {score}/100")
        lines.append("")
        lines.append(f"**评分依据**: {ds.rationale}")
        lines.append("")
        return lines

    def _top1_ranking_table(
        self, candidates: List[EvaluatedCandidate], weights: Dict[str, float]
    ) -> List[str]:
        lines: List[str] = ["## 2. 全量排名与六维评分", ""]
        if not candidates:
            lines.append("暂无候选方向。")
            lines.append("")
            return lines

        # Print weights
        lines.append("**评分权重**:")
        for dim, w in weights.items():
            lines.append(f"- {dim}: {int(w * 100)}%")
        lines.append("")

        # Print table header
        lines.append("| 排名 | 候选方向 | 总分 | 成熟度 | 市场 | 壁垒 | 规模化 | 成本 | 时机 | 来源数 |")
        lines.append("|------|---------|------|--------|------|------|--------|------|------|--------|")
        for c in candidates[:15]:
            ds = c.dimension_scores
            lines.append(
                f"| {c.ranking} | {c.name} | **{c.total_score}** | "
                f"{ds.maturity} | {ds.market} | {ds.moat} | "
                f"{ds.scalability} | {ds.cost} | {ds.timing} | {c.source_count} |"
            )
        lines.append("")
        return lines

    def _top1_deep_dive(self, top: EvaluatedCandidate) -> List[str]:
        lines: List[str] = ["## 3. Top 1 深度分析", ""]
        lines.append(f"### {top.name}")
        if top.tech_route:
            lines.append(f"**技术路线**: {top.tech_route}")
        if top.energy_type:
            lines.append(f"**能源类型**: {top.energy_type}")
        lines.append("")

        # Rebuild TechnologyProfile objects from dicts for formatting
        profiles: List[TechnologyProfile] = []
        for p_dict in top.profiles:
            try:
                profiles.append(TechnologyProfile.model_validate(p_dict))
            except Exception:
                pass

        if profiles:
            lines.append("#### 代表性案例")
            for idx, p in enumerate(profiles[:5], 1):
                lines.extend(self._format_profile(p, idx))
            lines.append("")

        # Evidence signals grouped by dimension
        if top.evidence_signals:
            lines.append("#### 关键证据信号")
            by_dim: Dict[str, List[Any]] = {}
            for s in top.evidence_signals:
                by_dim.setdefault(s.dimension, []).append(s)
            for dim, sigs in by_dim.items():
                lines.append(f"**{dim}**:")
                for s in sigs[:5]:
                    lines.append(f"- [{s.signal_type}] {s.description} (强度{s.strength})")
            lines.append("")

        # Score breakdown
        ds = top.dimension_scores
        lines.append("#### 六维评分详解")
        lines.append(f"- **技术成熟度 ({ds.maturity})**: {'高' if ds.maturity >= 70 else '中' if ds.maturity >= 40 else '低'} — 是否有海试、并网、量产等硬里程碑")
        lines.append(f"- **市场与政策 ({ds.market})**: {'高' if ds.market >= 70 else '中' if ds.market >= 40 else '低'} — 招标、订单、政策支持情况")
        lines.append(f"- **技术壁垒 ({ds.moat})**: {'高' if ds.moat >= 70 else '中' if ds.moat >= 40 else '低'} — 专利、认证、独家技术")
        lines.append(f"- **规模化潜力 ({ds.scalability})**: {'高' if ds.scalability >= 70 else '中' if ds.scalability >= 40 else '低'} — 模块化、可复制性")
        lines.append(f"- **成本趋势 ({ds.cost})**: {'高' if ds.cost >= 70 else '中' if ds.cost >= 40 else '低'} — LCOE、供应链成熟度")
        lines.append(f"- **时间窗口 ({ds.timing})**: {'高' if ds.timing >= 70 else '中' if ds.timing >= 40 else '低'} — 近期信号密度、爆发前夜判断")
        lines.append("")

        if ds.rationale:
            lines.append(f"**综合判断**: {ds.rationale}")
            lines.append("")

        return lines

    def _top1_risk_analysis(self, top: EvaluatedCandidate | None) -> List[str]:
        lines: List[str] = ["## 4. 风险与不确定性", ""]
        if not top:
            lines.append("无可分析对象。")
            lines.append("")
            return lines

        # Extract limitations / uncertainty from profiles
        limitations: List[str] = []
        uncertainties: List[str] = []
        for p_dict in top.profiles:
            lims = p_dict.get("limitations", []) if isinstance(p_dict, dict) else []
            if isinstance(lims, list):
                limitations.extend(lims)
            unc = p_dict.get("uncertainty_note", "") if isinstance(p_dict, dict) else ""
            if unc:
                uncertainties.append(unc)

        if limitations:
            lines.append("**已知局限**:")
            for lim in limitations[:5]:
                lines.append(f"- {lim}")
            lines.append("")

        if uncertainties:
            lines.append("**不确定性**:")
            for u in uncertainties[:5]:
                lines.append(f"- {u}")
            lines.append("")

        # Infer risks from low-scoring dimensions
        ds = top.dimension_scores
        weak_dims = []
        if ds.maturity < 50:
            weak_dims.append("技术成熟度不足，距离商业化可能还有较长周期")
        if ds.market < 50:
            weak_dims.append("市场信号弱，政策或订单支撑不明确")
        if ds.moat < 50:
            weak_dims.append("技术壁垒低，易被竞争对手复制或超越")
        if ds.scalability < 50:
            weak_dims.append("规模化路径不清晰，产能扩张存在不确定性")
        if ds.cost < 50:
            weak_dims.append("成本下降缓慢，经济性尚未得到验证")
        if ds.timing < 50:
            weak_dims.append("时间窗口不够明确，爆发时点难以判断")

        if weak_dims:
            lines.append("**评估提示的风险**:")
            for risk in weak_dims:
                lines.append(f"- {risk}")
            lines.append("")
        else:
            lines.append("各维度评分均处于健康区间，暂未识别出显著风险。")
            lines.append("")

        return lines

    def _top1_recommendations(self, top: EvaluatedCandidate | None) -> List[str]:
        lines: List[str] = ["## 5. 建议与下一步行动", ""]
        if not top:
            lines.append("建议扩大搜索范围或放宽时间窗口后重新评估。")
            lines.append("")
            return lines

        lines.append(f"针对 **{top.name}** 的后续建议:")
        lines.append("")

        ds = top.dimension_scores
        if ds.maturity < 70:
            lines.append("- [跟踪] 密切关注下一阶段海试/并网/量产里程碑的进展")
        if ds.market < 70:
            lines.append("- [补证] 补充收集招标公告、政府政策、大额订单等市场信号")
        if ds.moat < 70:
            lines.append("- [分析] 深入调研核心技术专利布局和标准认证状态")
        if ds.timing >= 70:
            lines.append("- [ urgency ] 时间窗口有利，建议加快跟踪频率，避免错过关键节点")

        lines.append("")
        return lines

    def _top1_sources(self, top: EvaluatedCandidate | None) -> List[str]:
        lines: List[str] = ["## 6. 来源", ""]
        if not top or not top.evidence_signals:
            lines.append("暂无来源记录。")
            lines.append("")
            return lines

        seen: set[str] = set()
        for s in top.evidence_signals:
            url = s.source_url
            if url and url not in seen:
                seen.add(url)
                lines.append(f"- {url}")
        lines.append("")
        return lines

    # ------------------------------------------------------------------ #
    # Profile formatter
    # ------------------------------------------------------------------ #

    def _format_profile(self, p: TechnologyProfile, index: int) -> List[str]:
        lines: List[str] = []
        lines.append(f"**案例 {index}: {p.name}**")

        meta: List[str] = []
        if p.company:
            meta.append(f"公司:{p.company}")
        if p.country:
            meta.append(f"国家:{p.country}")
        if p.capacity:
            meta.append(f"容量:{p.capacity}")
        if p.maturity:
            meta.append(f"成熟度:{p.maturity}")
        if meta:
            lines.append(" | ".join(meta))

        if p.advantages:
            lines.append(f"- 优势: {'；'.join(p.advantages[:3])}")
        if p.limitations:
            lines.append(f"- 局限: {'；'.join(p.limitations[:3])}")
        if p.timeline:
            ms = [f"{m.date or '?'}:{m.event}" for m in p.timeline[:3] if m.event]
            if ms:
                lines.append(f"- 里程碑: {' | '.join(ms)}")
        if p.significance:
            lines.append(f"- 战略意义: {p.significance[:150]}")

        lines.append("")
        return lines

    # ------------------------------------------------------------------ #
    # Generic sections (for build() method)
    # ------------------------------------------------------------------ #

    def _section_overview(self, package: IntelligenceReportPackage) -> List[str]:
        lines: List[str] = ["## 1. 主题概览", ""]
        lines.append(
            f"本期情报围绕 **{package.topic}** 展开，"
            f"共收集并分析了 {len(package.cases)} 个代表性案例与技术方向。"
        )
        if package.trend_analysis and package.trend_analysis.editorial_note:
            lines.append("")
            lines.append(package.trend_analysis.editorial_note)
        lines.append("")
        return lines

    def _section_background(self, package: IntelligenceReportPackage) -> List[str]:
        lines: List[str] = ["## 2. 技术背景与分类", ""]
        clusters = self._cluster_by_tech_route(package.cases)
        if clusters:
            lines.append("按技术路线归类如下：")
            for route, cases in clusters.items():
                lines.append(f"- **{route}**: {len(cases)} 个案例")
        else:
            lines.append("暂无明确技术路线分类。")
        lines.append("")
        return lines

    def _section_cases(self, package: IntelligenceReportPackage) -> List[str]:
        lines: List[str] = ["## 3. 代表性案例", ""]
        if not package.cases:
            lines.append("本期未收集到符合条件的案例。")
            lines.append("")
            return lines
        for idx, case in enumerate(package.cases[:15], start=1):
            lines.extend(self._format_profile(case, idx))
        lines.append("")
        return lines

    def _section_comparison(self, package: IntelligenceReportPackage) -> List[str]:
        lines: List[str] = ["## 4. 横向比较分析", ""]
        comp = package.comparison
        if not comp or not comp.dimensions:
            lines.append("案例数量或多样性不足，暂无法生成深度比较。")
            lines.append("")
            return lines
        for dim in comp.dimensions:
            lines.append(f"### {dim.dimension}")
            lines.append(dim.observation)
            if dim.stronger_cases:
                lines.append(f"- 表现较强：{', '.join(dim.stronger_cases)}")
            if dim.weaker_cases:
                lines.append(f"- 表现较弱：{', '.join(dim.weaker_cases)}")
            if dim.note:
                lines.append(f"- 备注：{dim.note}")
            lines.append("")
        if comp.key_differences:
            lines.append("**关键差异**")
            for diff in comp.key_differences:
                lines.append(f"- {diff}")
            lines.append("")
        if comp.notable_patterns:
            lines.append("**行业模式**")
            for pat in comp.notable_patterns:
                lines.append(f"- {pat}")
            lines.append("")
        if comp.commercialization_observation:
            lines.append(f"**商业化观察**：{comp.commercialization_observation}")
            lines.append("")
        if comp.engineering_observation:
            lines.append(f"**工程观察**：{comp.engineering_observation}")
            lines.append("")
        return lines

    def _section_trends(self, package: IntelligenceReportPackage) -> List[str]:
        lines: List[str] = ["## 5. 行业信号与趋势", ""]
        trend = package.trend_analysis
        if not trend:
            lines.append("暂无足够数据生成趋势分析。")
            lines.append("")
            return lines
        if trend.observed_trends:
            lines.append("### 观察到的趋势")
            for t in trend.observed_trends:
                lines.append(f"- {t}")
            lines.append("")
        if trend.bottlenecks:
            lines.append("### 技术与产业瓶颈")
            for b in trend.bottlenecks:
                lines.append(f"- {b}")
            lines.append("")
        if trend.opportunity_areas:
            lines.append("### 潜在机会领域")
            for o in trend.opportunity_areas:
                lines.append(f"- {o}")
            lines.append("")
        if trend.watchpoints:
            lines.append("### 值得跟踪的要点")
            for w in trend.watchpoints:
                lines.append(f"- {w}")
            lines.append("")
        return lines

    def _section_editorial(self, package: IntelligenceReportPackage) -> List[str]:
        lines: List[str] = ["## 6. 编辑解读与启示", ""]
        note = ""
        if package.trend_analysis and package.trend_analysis.editorial_note:
            note = package.trend_analysis.editorial_note
        elif package.comparison and package.comparison.commercialization_observation:
            note = package.comparison.commercialization_observation
        else:
            note = (
                "基于现有证据，建议优先关注技术成熟度较高、"
                "具备标准化/认证信号的方向；对信号强但证据薄的方向，"
                "建议下一轮重点补证。"
            )
        lines.append(note)
        lines.append("")
        return lines

    def _section_gaps(self, package: IntelligenceReportPackage) -> List[str]:
        lines: List[str] = ["## 7. 信息缺口与待验证问题", ""]
        if not package.gaps:
            lines.append("暂无明确识别的信息缺口。")
            lines.append("")
            return lines
        for gap in package.gaps:
            priority_label = f"[{gap.priority.upper()}]" if gap.priority else "[MEDIUM]"
            lines.append(f"- {priority_label} {gap.gap}")
            lines.append(f"  - 重要性：{gap.why_it_matters}")
        lines.append("")
        return lines

    def _section_sources(self, package: IntelligenceReportPackage) -> List[str]:
        lines: List[str] = ["## 8. 来源", ""]
        if not package.sources:
            lines.append("暂无来源记录。")
            lines.append("")
            return lines
        for s in package.sources:
            parts: List[str] = []
            if s.title:
                parts.append(s.title)
            if s.organization:
                parts.append(f"({s.organization})")
            if s.url:
                parts.append(f"<{s.url}>")
            if s.publication_date:
                parts.append(s.publication_date)
            lines.append(f"- {' '.join(parts)}")
        lines.append("")
        return lines

    def _cluster_by_tech_route(
        self, profiles: List[TechnologyProfile]
    ) -> Dict[str, List[TechnologyProfile]]:
        clusters: Dict[str, List[TechnologyProfile]] = {}
        for p in profiles:
            key = (p.tech_route or p.energy_type or "未分类").strip()
            clusters.setdefault(key, []).append(p)
        return clusters
