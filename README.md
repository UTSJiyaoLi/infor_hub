# Infor Hub

Infor Hub 是面向海洋新能源情报的任务化分析系统。
当前采用：**FastAPI 后端 + Next.js 前端 + SSH 端口转发连接远端服务**。

## 服务器上需要运行的后端组件

在 `gpu6000`（通过 `lijiyao` 跳板）只需要运行：

1. **Infor Hub API**
   - 启动命令：`uvicorn api.app:app --host 127.0.0.1 --port 8000`
2. **vLLM(Qwen) 服务**（你已有，不在本仓库内）
   - 由远端容器中的既有服务提供

本地前端通过 SSH 隧道访问后端 API，不需要在服务器运行 Next.js。

## API

- `GET /health`
- `POST /tasks`
- `GET /tasks/{task_id}`
- `POST /report/stream`（SSE）
- `POST /collect`（同步兼容接口）

## 任务落盘

- 任务状态：`outputs/tasks/<task_id>.json`
- 产物目录：`outputs/<task_id>/`
  - `result.json`
  - `final_report.md`

## 核心业务模块

- `services/source_registry.py`
- `services/collector.py`
- `services/parser_normalizer.py`
- `services/signal_extractor.py`
- `services/candidate_discovery.py`
- `services/evidence_builder.py`
- `services/scoring_engine.py`
- `services/report_agent.py`
- 编排入口：`services/pipeline_v2.py`

## 配置

- `.env.example`：默认配置模板
- `.env.local`：本地覆盖
- `settings.py`：统一读取配置
- `configs/source_registry.json`：来源注册表

## 目录（清理后）

```text
C:/Infor_hub/
  api/
  apps/web/
  configs/
  observability/
  orchestration/
  schemas/
  scripts/
  services/
  storage/
  tests/
  tools/
  settings.py
  requirements.txt
```

## 连接方式（与 wind-agent 对齐）

### 远端管理

```powershell
.\scripts\ops\infor_services.cmd status
.\scripts\ops\infor_services.cmd start
.\scripts\ops\infor_services.cmd health
.\scripts\ops\infor_services.cmd logs
.\scripts\ops\infor_services.cmd stop
```

### 本地一键联通（隧道 + 前端）

```powershell
.\scripts\ops\start_web_local.cmd
# 或指定本地端口
.\scripts\ops\start_web_local.cmd 18000
```

前端中 `Backend URL` 填脚本输出的本地地址（如 `http://127.0.0.1:18000`）。

## 本地测试（rag_task）

```powershell
conda run -n rag_task python -m pytest -q tests/test_api_endpoints.py tests/test_layering_imports.py
```
