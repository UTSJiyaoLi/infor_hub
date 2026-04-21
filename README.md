# Infor Hub - 离岸可再生能源情报收集系统

一个专业的AI驱动的技术情报收集和分析平台，专注于离岸可再生能源领域的研究和报告生成。

## 项目概述

**Infor Hub** 是一个高级情报收集系统，集成了 LangGraph 和多智能体工作流，用于：

- 🌊 **离岸可再生能源** - 离岸风能、浮动光伏、波浪能、潮流能等
- 🏭 **海洋工程技术** - 海上装备、系统集成、工程参数提取
- ⚡ **离岸氢能** - 氢气生产、能源转换、商业化进展
- 📊 **情报分析** - 技术对比、商业化信号、发展趋势分析

系统自动处理以下流程：

1. **信息收集** - 从多个来源收集原始数据
2. **结构化提取** - 提取工程参数、时间线、技术方案
3. **案例分析** - 识别并对比代表性项目和商业案例
4. **智能合成** - 生成专业工程情报简报

## 核心特性

### 专业情报输出

不同于通用的总结和博客文章，本系统生成**工程情报级别**的输出：

- ✅ 清晰的主题定义和技术背景
- ✅ 国内外代表性案例（≥3个）
- ✅ 结构化的技术方案对比
- ✅ 详细的工程参数和规范
- ✅ 产业进展和商业化信号
- ✅ 编辑风格的专业解读
- ✅ 可操作性的结论和建议

### 信息来源优先

系统遵循严格的信息追溯原则：

- 优先采用**官方来源** - 公司、项目、研究机构
- 其次使用**技术报告** - 学术论文、规范标准
- 参考**行业媒体** - 工程新闻、产业动态
- 避免未支持的主观声明

### 结构化优于冗长文本

在生成长篇报告前，系统首先组织结构化材料：

- 技术方案路线
- 产品/系统名称
- 企业/机构信息
- 国家/地区
- 应用场景
- 规模容量
- 部署方式
- 工程特性
- 优势与限制
- 成熟度/商业化状态
- 时间线/里程碑

## 项目结构

```markdown
c:\Infor_hub/
├── agent.md              # 系统设计文档 - 核心原理和工作方法
├── agent.py              # 智能体实现 - 工具定义和任务管理
├── graph.py              # 执行引擎 - LangGraph工作流入口
├── run.py                # 演示脚本 - 完整工作流示例
├── prompts.py            # 提示词管理 - AI指令和输出格式
├── tools.py              # 工具库 - 分解、分析、生成等功能
├── langgraph.json        # 图配置文件 - 工作流节点和边定义
├── requirements.txt      # 依赖清单 - Python包版本要求
├── structure.md          # 旧架构文档 - 参考（已演进）
│
├── schemas/              # 数据模型
│   ├── __init__.py
│   └── technology.py     # 技术档案数据模型
│                         # - EngineeringParameter (工程参数)
│                         # - SourceReference (来源引用)
│                         # - TimelineMilestone (时间线)
│                         # - TechnologyProfile (完整档案)
│
└── workflows/            # 工作流定义
    ├── __init__.py
    └── research_flow.py  # 研究流程图
                          # - 初始化
                          # - 主题分解
                          # - 源规划
                          # - 信息抓取与总结
                          # - 档案提取与合并
                          # - 案例对比
                          # - 趋势分析
                          # - 报告生成
```

### 关键模块说明

| 模块 | 用途 | 主要功能 |
| ------ | ------ | -------- |
| `agent.py` | 工具定义 | 任务创建、信息收集、档案管理、报告生成 |
| `graph.py` | 工作流执行 | 模型初始化、图构建、输入验证 |
| `tools.py` | 分析工具库 | 主题分解、来源规划、档案提取、对比分析 |
| `prompts.py` | AI指令 | 系统提示、角色定义、输出格式约束 |
| `run.py` | 演示脚本 | 完整工作流运行示例 |

## 技术栈

### 必需依赖

```markdown
langgraph>=0.0.40        # 工作流编排框架
langchain>=0.2.0         # LLM集成框架
langchain-core>=0.2.0    # 核心组件
pydantic>=2.6.0          # 数据验证和模型定义
typing-extensions>=4.9.0 # Python类型注解
requests>=2.31.0         # HTTP客户端
openai>=1.30.0           # OpenAI API集成
```

### 可选依赖

- `deepagents` - 深层级Agent支持
- `tavily` - Web搜索能力
- `beautifulsoup4` - HTML解析 (在agent.py中使用)

## 工作流程

### 完整执行流程

```markdown
1. 创建任务 (create_collection_task)
   └─> 初始化工作区、日志、数据文件

2. 主题分解 (decompose_topic)
   └─> 提取关键概念、搜索方向、过滤条件

3. 来源规划 (plan_source_collection)
   └─> 生成搜索查询、确定搜索策略

4. 信息收集 (summarize_source)
   └─> 抓取网页、提取信息、生成概要

5. 档案提取 (extract_profiles_from_source_summaries)
   └─> 识别技术、产品、企业信息
   └─> 提取工程参数、时间线、来源引用

6. 档案合并 (merge_profile_lists)
   └─> 去重合并、关系建立

7. 案例对比 (compare_cases)
   └─> 对比技术方案、商业化进度、优劣分析

8. 趋势分析 (analyze_trends)
   └─> 产业走向、技术发展方向、投资信号

9. 报告生成 (generate_final_report)
   └─> 编辑整合、格式化、输出最终智能简报
```

### 输出工件

每个任务生成以下输出文件（存放在 `workspace/runs/<task_id>/`）：

| 文件 | 描述 |
| ------ | ------ |
| `task.json` | 任务配置和元数据 |
| `raw_sources.jsonl` | 原始收集的信息源 |
| `extracted_notes.jsonl` | 结构化提取的笔记和档案 |
| `notes.md` | Markdown格式的详细笔记 |
| `timeline.md` | 时间线总结 |
| `gaps.md` | 分析空白和建议 |
| `report.md` | 最终情报简报 |

## 使用指南

### 安装依赖

```bash
pip install -r requirements.txt
```

### 快速开始

#### 方式1：运行演示脚本

```bash
python run.py
```

这将使用预定义的示例数据（波浪能、离岸氢能）运行完整工作流。

#### 方式2：自定义任务

```python
from graph import run_collector

# 准备输入数据
inputs = {
    "topic": "浮动式海上风电",
    "user_goal": "生成技术对比和商业化进展分析",
    "raw_sources": [
        {
            "title": "XXX项目总结",
            "source_type": "report",
            "url": "https://example.com/...",
            "text": "详细的项目信息..."
        },
        # ... 更多数据源
    ]
}

# 执行工作流
result = run_collector(inputs)

# 获取输出
print(result["report"])
print(result["timeline"])
print(result["opportunities"])
```

### 环境变量配置

```bash
# 模型选择（默认: openai:gpt-4o）
export COLLECTOR_MODEL="openai:gpt-4o"
# 或其他兼容模型
export COLLECTOR_MODEL="anthropic:claude-3-7-sonnet-latest"

# 工作区路径（默认: .collector_workspace）
export COLLECTOR_WORKSPACE="./my_workspace"

# 最大结果数（默认: 5）
export COLLECTOR_MAX_RESULTS="10"
```

## 数据模型

### TechnologyProfile

从信息源中提取的完整技术档案：

```python
{
  "technology_name": "CorPower C4",
  "category": "point_absorber",
  "description": "...",
  "engineering_parameters": [
    {
      "field_name": "installed_capacity",
      "value": "2",
      "unit": "MW",
      "note": "single device"
    }
  ],
  "companies": ["CorPower Ocean"],
  "countries": ["Sweden"],
  "application_scenarios": ["offshore", "deep_water"],
  "maturity_status": "demonstration",
  "advantages": ["high_capture_efficiency", "storm_survival"],
  "limitations": ["prototype_stage"],
  "timeline": [
    {
      "date": "2020-04",
      "event": "First full-scale prototype deployed",
      "status": "deployed"
    }
  ],
  "source_references": [
    {
      "title": "CorPower Ocean Project",
      "url": "https://...",
      "source_type": "official"
    }
  ]
}
```

## 核心工作原理

### 源优先原则 (Source-backed First)

系统严格遵循信息溯源制：

1. **官方来源优先** - 公司官网、项目声明、认证机构
2. **技术可信性** - 学术论文、工程报告、行业标准
3. **媒体参考** - 工程新闻、行业动态
4. **避免推测** - 不基于未支持的主观评论提出主张

### 结构优于冗长 (Structure Before Prose)

在撰写长篇报告前，优先提取结构化信息：

- 按照数据模型标准化信息
- 保留原始来源链接
- 支持信息追溯和验证
- 便于跨项目对比分析

### 案例为证 (Cases Are Essential)

每个主题至少包含：

- ≥3个代表性案例
- 同时涵盖国内外项目
- 既有商业应用又有示范项目
- 具体的工程参数和规模数据

## 扩展和定制

### 添加新的工具函数

在 `tools.py` 中使用 `@tool` 装饰器：

```python
from langchain_core.tools import tool

@tool
def my_analysis_tool(input_data: str) -> str:
    """Tool description for Claude."""
    # 实现逻辑
    return result
```

### 定制提示词

编辑 `prompts.py` 中的系统提示和角色定义，调整：

- 分析风格和深度
- 输出格式和结构
- 信息过滤标准

### 扩展数据模型

在 `schemas/technology.py` 中扩展 Pydantic 模型，如：

```python
class CustomProfile(TechnologyProfile):
    custom_field: Optional[str] = Field(...)
```

## 开发说明

### 日志和调试

系统在 `workspace/runs/<task_id>/` 下生成详细日志：

- 查看中间步骤的日志记录
- 检查提取的结构化数据
- 跟踪工作流执行过程

### 测试新配置

```bash
# 运行演示验证基础功能
python run.py

# 检查输出文件
ls -la .collector_workspace/*/
cat .collector_workspace/*/report.md
```

## 配置示例

### 基础配置 (requirements.txt)

```txt
langgraph>=0.0.40
langchain>=0.2.0
langchain-core>=0.2.0
pydantic>=2.6.0
typing-extensions>=4.9.0
requests>=2.31.0
openai>=1.30.0
```

## 常见问题

### Q: 如何增加收集的信息源数量？

A: 修改环境变量 `COLLECTOR_MAX_RESULTS` 或在 `tools.py` 中的 `plan_source_collection` 调整搜索策略。

### Q: 系统支持什么模型？

A: 支持所有 LangChain 兼容的模型：

- OpenAI: `openai:gpt-4o`, `openai:gpt-4-turbo`
- Anthropic: `anthropic:claude-3-7-sonnet-latest`
- 本地部署: 通过 LangChain 集成

### Q: 如何自定义输出格式？

A: 编辑 `prompts.py` 中的报告模板，或在 `tools.py` 的 `generate_final_report` 函数中修改格式化逻辑。

## 贡献与许可

欢迎提交问题报告和改进建议！

---

**最后更新**: 2026年4月8日  
**项目状态**: 活跃开发中  
**主要文档**: 查看 [agent.md](agent.md) 了解详细的设计和工作原理
