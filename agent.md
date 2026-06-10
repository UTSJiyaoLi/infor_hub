# InforHub 项目总览与 Agent 工作规范

## 1. 项目定位

### 1.1 背景

InforHub 是面向海洋新能源情报的任务化分析系统，当前采用 **FastAPI 后端 + Next.js 前端 + SSH 端口转发连接远端服务** 的架构。

项目出发点是为了响应"信息收集器 + 智能筛选器 + 文档化输出"的业务需求。领导希望建设一套面向专业领域的信息服务系统，能够完成：

1. 持续获取领域内最新信息、知识资料和分析依据。
2. 对海量信息做筛选、排序和重点推荐，降低人工检索成本。
3. 将高价值内容进一步整理成结构化结论或报告，直接交付给用户。

### 1.2 一句话概括

> 系统先把专业资料转成可检索的知识库，再通过大模型和规则路由判断用户需求，自动选择"直接回答、知识检索回答、还是调用分析工具"，最后把最相关、最有依据的结果整理成可读结论、结构化数据和图表输出给用户。

### 1.3 目标用户

- 行业研究员
- 战略团队
- 投资与业务决策者
- 高管简报撰写人员

---

## 2. 系统架构

系统拆为 5 层：

### 2.1 模型层

- 使用 OpenAI `Responses API` 或本地 vLLM(Qwen) 服务
- 如需多 agent 协作，可引入 `Agents SDK`
- 职责：多轮推理、工具调度、流式输出、结构化结果生成

### 2.2 工具层

- `web_search` — 查询近 6-12 个月行业动态、官方报告、协会数据
- `file_search` — 检索内部模板、历史简报、术语库、研究底稿
- `mcp` 或自定义函数调用 — 接内部 CMS、企业数据库、行业 API、图表服务
- 图片/图表生成工具 — 生成封面图、示意图、图表预览

### 2.3 规范层 (SKILL.md)

SKILL.md 不是官方 API 的原生对象，而是项目自己的工作流规范层。

建议拆成多个可组合 skill：

- `industry-briefing/SKILL.md`
- `research-recent-sources.md`
- `fact-check-and-citation.md`
- `chart-and-visual.md`
- `final-briefing-output.md`

### 2.4 编排层

Orchestrator 负责：

- 解析用户任务
- 选择合适 skill
- 分派给研究、核验、成稿、审校等子流程
- 管理中间状态和失败重试

当前已实现的关键节点：

1. `input_preprocess`
2. `domain_router`
3. `mode_router`
4. `policy_gate`
5. `flow_entry`
6. `clarify_node`
7. `fallback_or_escalation`
8. `workflow_planner`
9. `rag_executor`
10. `tool_executor`
11. `answer_synthesizer`

后续可升级为多 agent：Research Agent / Fact-check Agent / Brief Writer Agent / Review Agent。

### 2.5 前端体验层

前端不展示模型内部思维，而展示可审计工作流：

- 当前阶段
- 正在调用的工具
- 读取到的模板/文件
- 已确认的来源
- 已生成的图表/图片
- 草稿更新记录
- 待核验数据点

---

## 3. 核心能力

### 3.1 知识采集与知识库构建

- 解析 PDF 等专业资料，提取文本、页码、图片/表格相关信息
- 将长文档切分为可检索的知识片段
- 为每个知识片段生成向量表示和稀疏索引信息
- 把处理结果写入 Milvus 向量数据库，形成可查询的领域知识库
- 同时保存轻量元数据和完整元数据，兼顾检索效率和结果追溯

### 3.2 智能检索与知识增强问答 (RAG)

- 支持向量检索和 BM25 稀疏检索混合召回
- 支持 query rewrite，对用户问题做改写，提升召回率
- 支持领域扩展，将问题扩展为更接近专业术语的检索表达
- 支持 rerank，对候选结果再次排序，提高命中质量
- 支持复杂问题拆分为多个子问题，再分别检索后综合回答
- 支持答案引用上下文片段，提升结果可解释性
- 支持对检索质量和答案质量打分，形成可观测闭环

### 3.3 智能体编排 (LangGraph)

Agent 主流程把用户请求转成一套可执行的决策流程：

- 先理解用户属于哪类问题
- 再判断应该走哪种处理模式
- 如果需要专业工具分析，就自动进入工具执行链路
- 如果需要知识问答，就进入 RAG
- 如果信息不完整，就要求补充必要参数
- 最后统一输出成中文结论

### 3.4 专业分析工具

**风资源分析工具**

系统可以读取 Excel 风况数据并自动完成分析，输出结构化指标和图表：

- 风向频率分布
- 平均风速统计
- Weibull 拟合
- 风速直方图
- 联合概率分布图
- 多张分析图自动保存输出

**台风风险分析工具**

系统支持基于历史统计结果进行台风概率分析，并可进一步生成地图可视化结果：

- 命中概率
- 年尺度概率
- 样本数
- 台风影响范围
- 地图展示信息

### 3.5 最新情报采集与分析 (TIDE Pipeline v3)

这是面向互联网最新动态的核心能力，也是"信息收集器"目标的前端补齐：

- **搜索编排**：统一 Tavily / DDGS / SearxNG 三种搜索后端
- **内容解析**：LLM 结构化提取 TechnologyProfile
- **信号提取**：LLM 六维证据信号提取
- **候选聚类**：自动按技术路线/案例名称聚类
- **六维评分**：成熟度/市场/壁垒/规模化/成本/时机
- **排名选优**：加权总分排序，选 Top 1
- **深度报告**：为 Top 1 生成固定格式情报简报

---

## 4. TIDE 情报分析算法

TIDE = Technology Intelligence Development Evaluation

### 4.1 算法流程

```
输入: 领域主题 topic，用户目标 user_goal，时间窗口 time_window
输出: Top 1 技术方向 + 深度情报报告 + 全量排名

Step 1: 信息获取 (Search)
  后端: DDGS/Tavily/SearxNG
  查询构造: {topic} latest breakthrough commercialization 2025 2026
  过滤: URL去重 → 域名白名单 → 全文抓取 → 质量过滤
  输出: List[RawDocument]

Step 2: 结构化提取 (Extract)
  ContentAnalyzer: 每篇 → TechnologyProfile
  SignalExtractorV2: 每篇 → EvidenceSignals (六维信号)
  过滤: 只保留相关度 > threshold 的文章

Step 3: 候选聚类 (Aggregate)
  按 (tech_route + name) 哈希分组
  每个聚类 = 候选方向 Cj
  Cj 包含: 所有相关 profile + 所有 evidence signals + 所有原始文章

Step 4: 六维评分 (Score)
  每个候选调用 1 次 LLM，输出 6 维度分数 (0-100) + 评分理由
  总分 = Σ(维度分 × 权重)

  默认权重:
    maturity(成熟度)   20%
    market(市场)       20%
    moat(壁垒)         15%
    scalability(规模化) 15%
    cost(成本)         15%
    timing(时机)       15%

  评分原则:
    - 只基于提供的证据打分，不要引入外部知识
    - 证据不足的方向相应维度给低分
    - 给出每个维度的具体评分理由

Step 5: 排名选优 (Rank)
  按总分降序
  选 Top 1：必须是总分最高 且 证据充分度 ≥ threshold（至少 2 篇独立来源）
  如果 Top 1 证据不足，降级推荐 Top 2

Step 6: Top 1 深度报告 (Report)
  用 C_top1 的所有证据做深度合成
  生成固定格式 8 节情报简报
  重点突出: 为什么它是 Top 1（优势分析 + 风险提示）
```

### 4.2 六维评分详解

| 维度 | 权重 | 高分信号 | 低分信号 |
|------|------|---------|---------|
| **成熟度** | 20% | 海试完成、并网发电、量产交付、TRL≥7 | 仅概念阶段、无实物验证 |
| **市场** | 20% | 招标公告、GW级订单、政府补贴、国际合作 | 无商业订单、政策空白 |
| **壁垒** | 15% | 核心专利、DNV/AiP认证、独家技术合作 | 技术公开、无专利保护 |
| **规模化** | 15% | 模块化设计、产能扩张计划、阵列化部署 | 单台示范、无复制路径 |
| **成本** | 15% | LCOE下降曲线、供应链本土化、批量制造 | 成本居高不下、依赖进口 |
| **时机** | 15% | 近期密集报道、资本进入、产业链配套成熟 | 长期沉寂、竞品已领先 |

---

## 5. Agent 工作原则

### 5.1 Source-backed first

Always prioritize information that can be attributed to a specific source.

When making a claim, prefer:

1. official company / project / research institution sources
2. technical reports
3. standards or certification bodies
4. engineering news / industry media
5. secondary commentary

Do not present unsupported claims as facts.

### 5.2 Structure before prose

Before writing a long report, first organize the material into structure.

You should try to extract:

- technology route
- product / system name
- company / institution
- country / region
- application scenario
- capacity / scale
- deployment method
- engineering characteristics
- advantages
- limitations
- maturity / commercialization status
- timeline / milestone
- source link or source reference

Long prose is secondary. Structured intelligence is primary.

### 5.3 Cases are essential

For each topic, try to collect representative cases.

A good intelligence brief should usually include:

- at least 3 representative cases when possible
- both domestic and international examples when relevant
- both commercial and demonstration projects if applicable

Do not stop at conceptual description if concrete projects or products exist.

### 5.4 Compare technical routes

Do not simply list technologies. Compare them.

For any important topic, try to compare:

- technical principle
- deployment condition
- cost implications
- maintenance difficulty
- reliability
- scalability
- environmental impact
- commercialization readiness

If the topic has multiple routes, explicitly identify the differences.

### 5.5 Distinguish fact from interpretation

Always separate:

- factual description
- inferred engineering judgment
- editorial observation
- open question / uncertainty

Use wording that makes this separation clear.

Examples:

- "According to the source..."
- "This suggests that..."
- "A likely implication is..."
- "This still requires further validation..."

Do not mix speculation with confirmed facts.

### 5.6 Be engineering-oriented

When information is available, prioritize engineering and deployment details over publicity language.

Prefer extracting:

- MW / kW scale
- water depth
- structural form
- mooring type
- material
- installation method
- test duration
- operating condition
- grid connection status
- TRL or implied maturity
- CAPEX / LCOE / cost trends if available

Avoid spending too much space on slogans, positioning, or promotional statements.

### 5.7 Preserve uncertainty

If data is incomplete, contradictory, or preliminary, say so explicitly.

Use tags like:

- concept stage
- prototype
- tank-tested
- sea trial completed
- demonstration
- early commercial
- commercial deployment
- unclear / not disclosed

Never pretend certainty where the source does not support it.

---

## 6. 输出规范

### 6.1 固定格式 8 节情报简报

除非任务要求其他格式，报告应遵循以下结构：

1. **Topic Overview** — 主题概览与执行摘要
2. **Technical Background / Classification** — 技术背景与分类
3. **Representative Cases** — 代表性案例（结构化表格/列表）
4. **Comparative Analysis** — 横向比较分析
5. **Industry Signals / Trends** — 行业信号与趋势
6. **Editorial Notes / Implications** — 编辑解读与启示
7. **Open Questions / Gaps** — 信息缺口与待验证问题
8. **Sources** — 来源清单

对于 TIDE 算法的 Top 1 报告，结构调整为：

1. **执行摘要** — Top 1 是谁，总分多少，核心优势维度
2. **全量排名表** — 所有候选的六维分数对比（Markdown 表格）
3. **Top 1 深度分析** — 案例详情 + 关键证据信号 + 六维评分详解
4. **风险与不确定性** — 已知局限 + 低分维度风险提示
5. **建议与下一步行动** — 针对 Top 1 的跟踪建议
6. **来源** — 所有证据的 URL 清单

### 6.2 流式输出事件模型

前端不展示模型内部思维，而展示可审计工作流：

```ts
type AgentEvent =
  | { type: "step.started"; stepId: string; title: string }
  | { type: "step.updated"; stepId: string; message: string }
  | { type: "tool.called"; tool: string; inputPreview?: string }
  | { type: "tool.completed"; tool: string; outputSummary: string }
  | { type: "artifact.found"; kind: "file" | "source" | "image"; name: string; uri?: string }
  | { type: "citation.added"; sourceTitle: string; sourceUrl?: string }
  | { type: "draft.updated"; section: string; summary: string }
  | { type: "review.flagged"; item: string; reason: string }
  | { type: "result.completed"; artifactUrl?: string };
```

前端可映射为：

- Working 时间线
- 来源卡片
- 文件卡片
- 草稿片段预览
- 最终导出按钮

### 6.3 写作风格

Use a style that is:

- concise
- structured
- professional
- engineering-oriented
- readable by strategy, investment, and technical readers

Prefer:

- short paragraphs
- clear headings
- explicit comparison language
- concrete terminology
- restrained interpretation

Avoid:

- exaggerated promotional wording
- casual internet tone
- overly literary prose
- excessive repetition

---

## 7. 情报数据模型与 Ontology

### 7.1 TechnologyProfile

```
name                          # 名称
aliases                       # 别名
company                       # 主导公司
institution                   # 研究机构
consortium                    # 联合体
country / region              # 国家/地区
energy_type                   # 能源类型
tech_route                    # 技术路线
system_type                   # 系统类型
application_scenario          # 应用场景
deployment                    # 部署方式
structural_form               # 结构形式
mooring_or_foundation         # 系泊/基础类型
material_system               # 材料体系
installation_method           # 安装方法
capacity                      # 容量
water_depth                   # 水深
scale_description             # 规模描述
engineering_parameters        # 工程参数列表 [ {field_name, value, unit, note} ]
principle_of_operation        # 工作原理
key_components                # 关键部件
engineering_features          # 工程特征
advantages                    # 优势
limitations                   # 局限性
environmental_considerations  # 环境考量
maturity                      # 成熟度
commercialization_status      # 商业化状态
certification_status          # 认证状态
trl                           # 技术成熟度等级
significance                  # 战略意义
comparison_tags               # 比较标签
watchpoints                   # 跟踪要点
timeline                      # 时间线 [ {date, event, status} ]
sources                       # 来源引用 [ {title, organization, url, ...} ]
collector_note                # 采集者备注
uncertainty_note              # 不确定性备注
```

### 7.2 EvidenceSignal

```
dimension       # maturity / market / moat / scalability / cost / timing
signal_type     # 具体信号类型，如 sea_trial, grid_connection, tender, patent
description     # 信号描述
strength        # 强度 1-5
source_doc_id   # 来源文档ID
source_url      # 来源URL
```

### 7.3 DimensionScores

```
maturity        # 0-100
market          # 0-100
moat            # 0-100
scalability     # 0-100
cost            # 0-100
timing          # 0-100
rationale       # 评分理由
```

### 7.4 领域 Ontology

**Energy types**

- offshore wind
- floating wind
- wave energy
- tidal energy
- current energy
- floating solar
- offshore hydrogen
- integrated ocean energy
- energy islands
- offshore power-to-x

**Technology route examples**

- oscillating water column
- oscillating body
- overtopping
- point absorber
- submerged buoy
- semi-submersible
- spar
- tension leg platform
- barge
- distributed electrolysis
- centralized offshore electrolysis
- direct seawater electrolysis
- desalination plus electrolysis
- hybrid wind-wave
- hybrid wind-solar
- hydrogen/ammonia/methanol offshore conversion

**Maturity labels**

- concept
- lab validation
- tank test
- sea trial
- pilot
- demonstration
- pre-commercial
- commercial

---

## 8. 反模式与质量检查

### 8.1 Anti-Patterns

**1. Generic summaries**

Bad: "This technology has broad prospects."
Good: "This route is attractive because it reduces offshore heavy-lift dependence, but long-term survivability data is still limited."

**2. Pure source dumping**

Bad: long unstructured lists of links or copied snippets
Good: normalized cases plus concise interpretation

**3. Missing engineering details**

Bad: describing technology only in conceptual terms
Good: including power rating, structure, deployment condition, and maturity

**4. Excessive confidence**

Bad: "This route will become dominant."
Good: "This route appears promising for shallow-to-mid water deployment, but evidence of large-scale commercial deployment remains limited."

**5. Overwriting uncertainty**

Bad: converting unclear timeline or performance into definite statements
Good: marking data gaps and unresolved issues

### 8.2 Final Quality Checklist

Before considering the task complete, verify:

- Did I identify the main technology routes?
- Did I include representative cases?
- Did I extract concrete engineering parameters where available?
- Did I compare technologies rather than just list them?
- Did I clearly separate fact from interpretation?
- Did I preserve uncertainty?
- Does the output look like an intelligence brief rather than a casual summary?

If not, improve the result before finishing.

---

## 9. 版本规划

### V1（当前已完成）

1. 读取 SKILL.md 和简报模板
2. 检索内部知识库 (RAG)
3. 联网搜索近 6-12 个月来源 (TIDE Pipeline v3)
4. 生成带引用的简报草稿
5. 在前端流式展示工作过程

V1 输出形态：

- 聊天区中的结构化结果
- 一个可下载 Markdown 简报
- 一个来源附录

### V2（待扩展）

- 图表自动生成
- 封面图或配图生成
- 多 agent 分工
- 审校流程
- DOCX / PDF 导出
- 版本比对
- 定时任务自动出报告

---

## 10. 关键代码位置

| 模块 | 文件 |
|------|------|
| API 入口 | `api/app.py` |
| v2 流水线 | `services/pipeline_v2.py` |
| v3 TIDE 流水线 | `services/pipeline_v3.py` |
| 搜索编排 | `services/search_orchestrator.py` |
| 内容解析 | `services/content_analyzer.py` |
| 信号提取 | `services/signal_extractor_v2.py` |
| 候选聚类 | `services/candidate_aggregator.py` |
| 六维评分 | `services/scoring_engine.py` (ScoringEngine) |
| 报告生成 | `services/report_builder.py` |
| 数据模型 | `schemas/pipeline.py`, `schemas/technology.py` |
| 配置读取 | `settings.py` |
| 任务存储 | `storage/task_store.py` |
| 前端 | `apps/web/app/page.tsx` |
