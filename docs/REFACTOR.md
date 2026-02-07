# 紫微神算 - 前后端分离重构方案（v2）

## 一、重构目标

### 1.1 核心目标

将当前 Flask 模板渲染的单体架构升级为可持续演进的前后端分离架构：

- **后端**：Flask 纯 JSON API + 异步任务执行
- **前端**：React + Vite 独立 Web 应用
- **任务系统**：Redis + RQ Worker，解决长耗时请求阻塞

### 1.2 优秀级验收标准（SLO）

| 指标 | 目标 | 说明 |
|------|------|------|
| Analyze 首包响应 | `< 300ms` | `POST /api/analyze` 仅创建任务，不阻塞 |
| 结果可追踪 | 100% | 每个任务必须有 `task_id`、状态、进度、错误信息 |
| 可恢复性 | 100% | 浏览器刷新后可继续查询任务状态 |
| API 错误规范化 | 100% | 统一错误码 + `request_id` + 是否可重试 |
| 发布可回滚 | `< 5 分钟` | 具备版本回退与数据兼容策略 |

---

## 二、现有架构分析

### 2.1 当前项目结构

```
DeepSeek-Oracle/
├── app.py                    # Flask 主应用（路由+业务+数据库+模板渲染，耦合严重）
├── main.py                   # 空文件
├── json2ziwei/
│   ├── api.py                # 调用 iztro Node 服务获取星盘 JSON
│   └── convert.py            # 星盘 JSON → 文本描述
├── llmana/
│   ├── deepseekapi.py        # DeepSeek 官方 API
│   ├── deepseek_ali_api.py   # 阿里云 DeepSeek API
│   ├── deepseek_huoshan_api.py  # 火山引擎 API（当前使用）
│   ├── glmapi.py             # 智谱 GLM API
│   └── qwenmax_api.py        # 通义千问 API
├── token_ana/
│   └── deepseek_tokenizer.py # jieba 分词统计 token
├── src/
│   └── index.js              # iztro Express 服务（端口 3000）
├── templates/                # Jinja2 HTML 模板（5个页面）
├── static/                   # CSS + 图片
└── requirements.txt
```

### 2.2 当前问题

| 问题 | 说明 |
|------|------|
| 前后端耦合 | `app.py` 同时负责路由、业务逻辑、数据库操作、session 管理、模板渲染 |
| 状态依赖 session | 页面间通过 session 传值，天然不适合多端访问 |
| LLM 接口不统一 | 5 个 Provider 各自定义接口，切换成本高 |
| 同步阻塞 | 任务最长可达 30 分钟，HTTP 连接长时间占用 |
| 数据库操作散落 | SQLite 语句散落在路由函数中，无模型层抽象 |
| 错误处理缺失 | 无统一错误码、可重试标志、链路追踪 ID |
| 工程化不足 | 缺少异步任务、可观测性、灰度发布与回滚方案 |

---

## 三、目标架构（优秀版）

```
┌─────────────────────┐      HTTP      ┌────────────────────────────────────┐
│   React + Vite      │  ◄──────────►  │            Flask API                │
│   (Frontend :5173)  │                │            (Backend :5000)          │
└─────────────────────┘                │  ┌────────────────────────────────┐ │
                                       │  │ API / Services / Providers     │ │
                                       │  └──────────────┬─────────────────┘ │
                                       └─────────────────┼───────────────────┘
                                                         │ enqueue
                                                 ┌───────▼────────┐
                                                 │   Redis Queue    │
                                                 └───────┬────────┘
                                                         │ consume
                                                 ┌───────▼────────┐
                                                 │   RQ Worker      │
                                                 │  分析编排与重试   │
                                                 └───┬─────────┬───┘
                                                     │         │
                                          ┌──────────▼───┐  ┌──▼────────────┐
                                          │  SQLite/PG   │  │ iztro (3000)  │
                                          │  任务+结果存储 │  │ Node 星盘服务  │
                                          └──────────────┘  └───────────────┘
```

### 3.1 请求链路

1. 前端调用 `POST /api/analyze` 提交生辰参数。
2. 后端生成 `task_id` 并入队，立即返回 `202 Accepted`。
3. 前端轮询 `GET /api/task/<task_id>` 获取进度。
4. 任务完成后返回 `result_id`，前端跳转 `GET /api/result/<id>`。

> 备注：如果命中缓存，`POST /api/analyze` 直接返回 `200` + `result_id`，无需轮询。

---

## 四、后端重构方案

### 4.1 目录结构

```
backend/
├── app/
│   ├── __init__.py                 # Flask 应用工厂 create_app()
│   ├── config.py                   # 配置类（从 .env 读取）
│   │
│   ├── api/
│   │   ├── __init__.py             # 注册所有蓝图
│   │   ├── analyze.py              # POST /api/analyze
│   │   ├── task.py                 # GET /api/task/<task_id> 等
│   │   ├── history.py              # GET /api/history, GET /api/result/<id>
│   │   └── export.py               # GET /api/export/<id>
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── ziwei_service.py        # 调用 iztro + JSON 转文本
│   │   ├── llm_service.py          # LLM 调用编排（并发三项分析）
│   │   └── analysis_service.py     # 完整流程编排：命盘→LLM→存库
│   │
│   ├── workers/
│   │   ├── __init__.py
│   │   └── analysis_worker.py      # RQ Worker 任务入口
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── database.py             # 连接与事务封装
│   │   ├── task_repo.py            # 任务表 CRUD
│   │   └── result_repo.py          # 结果表 CRUD
│   │
│   ├── llm_providers/
│   │   ├── __init__.py
│   │   ├── base.py                 # BaseLLMProvider 抽象基类
│   │   ├── volcano.py              # 火山引擎 DeepSeek
│   │   ├── aliyun.py               # 阿里云 DeepSeek
│   │   ├── deepseek.py             # DeepSeek 官方
│   │   ├── glm.py                  # 智谱 GLM
│   │   └── qwen.py                 # 通义千问
│   │
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── tokenizer.py            # Token 统计
│   │   ├── response.py             # success()/error()
│   │   ├── errors.py               # 业务异常定义
│   │   └── logging.py              # 结构化日志
│   │
│   └── schemas/
│       ├── __init__.py
│       └── analysis.py             # 请求/响应校验（Pydantic 或 Marshmallow）
│
├── iztro_service/                  # iztro Node.js 服务
├── migrations/                     # SQL 迁移脚本
├── requirements.txt
├── run.py                          # API 启动入口
└── worker.py                       # RQ worker 启动入口
```

### 4.2 API 接口设计（异步优先）

#### 统一响应格式

成功响应：

```json
{
  "code": 0,
  "message": "ok",
  "data": {},
  "request_id": "req_20260207_xxx"
}
```

错误响应：

```json
{
  "code": "A1001",
  "message": "missing required field: date",
  "details": {
    "field": "date"
  },
  "retryable": false,
  "request_id": "req_20260207_xxx"
}
```

#### `POST /api/analyze` — 提交分析请求

请求：

```json
{
  "date": "2000-08-16",
  "timezone": 2,
  "gender": "女",
  "calendar": "solar",
  "provider": "volcano",
  "model": "deepseek-r1",
  "prompt_version": "v1"
}
```

返回场景 A（命中缓存，HTTP 200）：

```json
{
  "code": 0,
  "message": "cache_hit",
  "data": {
    "result_id": 128,
    "hit_cache": true
  },
  "request_id": "req_xxx"
}
```

返回场景 B（新建任务，HTTP 202）：

```json
{
  "code": 0,
  "message": "accepted",
  "data": {
    "task_id": "task_20260207_abcd",
    "status": "queued",
    "poll_after_ms": 2000,
    "hit_cache": false
  },
  "request_id": "req_xxx"
}
```

#### `GET /api/task/<task_id>` — 查询任务状态

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "task_id": "task_20260207_abcd",
    "status": "running",
    "progress": 66,
    "step": "llm_partner_character",
    "result_id": null,
    "error": null,
    "retry_count": 0,
    "updated_at": "2026-02-07T10:10:00Z"
  },
  "request_id": "req_xxx"
}
```

完成状态示例：

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "task_id": "task_20260207_abcd",
    "status": "succeeded",
    "progress": 100,
    "step": "done",
    "result_id": 128,
    "error": null,
    "retry_count": 0
  },
  "request_id": "req_xxx"
}
```

失败状态示例：

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "task_id": "task_20260207_abcd",
    "status": "failed",
    "progress": 45,
    "step": "llm_challenges",
    "result_id": null,
    "error": {
      "code": "A3001",
      "message": "llm timeout",
      "retryable": true
    },
    "retry_count": 1
  },
  "request_id": "req_xxx"
}
```

#### `POST /api/task/<task_id>/cancel` — 取消任务

- 仅允许 `queued/running` 状态取消。
- 已完成任务返回 `409 Conflict`。

#### `POST /api/task/<task_id>/retry` — 重试任务

- 仅允许 `failed` 状态重试。
- 最大重试次数由 `MAX_TASK_RETRY` 控制（默认 2）。

#### `GET /api/result/<id>` — 获取分析详情

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "id": 128,
    "birth_info": {
      "date": "2000-08-16",
      "timezone": 2,
      "gender": "女",
      "calendar": "solar"
    },
    "provider": "volcano",
    "model": "deepseek-r1",
    "prompt_version": "v1",
    "text_description": "----------基本信息----------\n命主性别：女\n...",
    "analysis": {
      "marriage_path": {
        "content": "婚姻道路分析内容...",
        "execution_time": 45.2,
        "token_count": 1234,
        "input_tokens": 456,
        "output_tokens": 778
      },
      "challenges": {
        "content": "困难挑战分析内容...",
        "execution_time": 38.7,
        "token_count": 1100,
        "input_tokens": 420,
        "output_tokens": 680
      },
      "partner_character": {
        "content": "伴侣性格分析内容...",
        "execution_time": 42.1,
        "token_count": 1180,
        "input_tokens": 430,
        "output_tokens": 750
      }
    },
    "total_execution_time": 126.0,
    "total_token_count": 3514,
    "created_at": "2026-02-07T10:12:00Z"
  },
  "request_id": "req_xxx"
}
```

#### `GET /api/history` — 获取历史记录列表（分页）

`GET /api/history?page=1&page_size=20`

#### `GET /api/export/<id>` — 下载 Markdown 报告

- 支持 `scope=full|marriage_path|challenges|partner_character`。

### 4.3 任务状态机

状态流转：

```
queued -> running -> succeeded
                 -> failed -> retrying -> queued
                 -> cancelled
```

进度建议：

| step | progress |
|------|----------|
| `queued` | 0 |
| `generate_chart` | 15 |
| `llm_marriage_path` | 45 |
| `llm_challenges` | 65 |
| `llm_partner_character` | 85 |
| `persist_result` | 95 |
| `done` | 100 |

### 4.4 LLM 抽象升级（Provider 无关）

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class LLMUsage:
    input_tokens: int
    output_tokens: int
    total_tokens: int

@dataclass
class LLMResult:
    content: str
    usage: LLMUsage
    latency_ms: int
    provider: str
    model: str
    finish_reason: str | None = None

class BaseLLMProvider(ABC):
    SYSTEM_PROMPT = "你是一个熟练紫微斗数的大师，请根据用户需求进行紫微斗数命盘分析。"

    @abstractmethod
    def generate(self, user_message: str, timeout_s: int = 1800) -> LLMResult:
        pass
```

统一约束：

- 所有 Provider 必须返回 `LLMResult`。
- 统一超时、重试、指数退避（建议 `1s/2s`，最多 2 次）。
- 原始异常转换为业务错误码，避免向前端暴露 SDK 细节。

### 4.5 数据库模型（结构化存储）

> 开发环境可用 SQLite；生产建议 PostgreSQL（并发写入稳定性更好）。

```sql
CREATE TABLE IF NOT EXISTS analysis_tasks (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  task_id TEXT NOT NULL UNIQUE,
  status TEXT NOT NULL,
  progress INTEGER NOT NULL DEFAULT 0,
  step TEXT,
  birth_date TEXT NOT NULL,
  timezone INTEGER NOT NULL,
  gender TEXT NOT NULL,
  calendar TEXT NOT NULL,
  provider TEXT NOT NULL,
  model TEXT NOT NULL,
  prompt_version TEXT NOT NULL,
  cache_key TEXT NOT NULL,
  result_id INTEGER,
  error_code TEXT,
  error_message TEXT,
  retry_count INTEGER NOT NULL DEFAULT 0,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  started_at DATETIME,
  finished_at DATETIME
);

CREATE INDEX IF NOT EXISTS idx_tasks_status_created_at
ON analysis_tasks(status, created_at DESC);

CREATE TABLE IF NOT EXISTS analysis_results (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  cache_key TEXT NOT NULL UNIQUE,
  birth_info_json TEXT NOT NULL,
  text_description TEXT NOT NULL,
  provider TEXT NOT NULL,
  model TEXT NOT NULL,
  prompt_version TEXT NOT NULL,
  total_execution_time REAL NOT NULL,
  total_token_count INTEGER NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS analysis_items (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  result_id INTEGER NOT NULL,
  analysis_type TEXT NOT NULL,
  content TEXT NOT NULL,
  execution_time REAL NOT NULL,
  input_tokens INTEGER NOT NULL,
  output_tokens INTEGER NOT NULL,
  token_count INTEGER NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(result_id, analysis_type)
);
```

缓存键建议：

```
cache_key = sha256(date|timezone|gender|calendar|provider|model|prompt_version)
```

### 4.6 错误码、安全、稳定性

#### 错误码规范

| 错误码 | HTTP | 含义 | 可重试 |
|--------|------|------|--------|
| `A1001` | 400 | 参数缺失/格式错误 | 否 |
| `A1002` | 422 | 业务参数非法（时辰范围等） | 否 |
| `A2001` | 502 | iztro 服务不可用 | 是 |
| `A3001` | 504 | LLM 超时 | 是 |
| `A3002` | 502 | LLM Provider 调用失败 | 是 |
| `A4004` | 404 | 任务或结果不存在 | 否 |
| `A4009` | 409 | 结果尚未就绪 | 是 |
| `A4290` | 429 | 请求频率过高 | 是 |
| `A5000` | 500 | 未知服务端错误 | 视情况 |

#### 安全与限流

- CORS 使用白名单（开发/生产分别配置），禁止全量 `*`。
- `POST /api/analyze` 增加 IP 级限流（如 `10 req/min`）。
- 输入参数严格校验（日期、时辰、枚举值）。
- 日志脱敏：不记录 API Key、完整 Prompt 原文。

### 4.7 可观测性（Observability）

- 结构化日志字段：`request_id`、`task_id`、`provider`、`model`、`latency_ms`、`status`。
- 指标（Prometheus 或等效方案）：
  - `analyze_submit_total`
  - `task_running_count`
  - `task_failed_total`
  - `llm_latency_ms_bucket`
  - `cache_hit_ratio`
- 健康检查：
  - `GET /healthz`（进程存活）
  - `GET /readyz`（数据库、Redis、iztro 连通）

### 4.8 文件迁移映射

| 原文件 | 目标位置 | 改动 |
|--------|---------|------|
| `app.py` 路由部分 | `app/api/*.py` | 去掉 `render_template`，改 JSON 接口 |
| `app.py` 业务逻辑 | `app/services/analysis_service.py` | 提取完整编排逻辑 |
| `app.py` 数据库操作 | `app/models/*.py` | 封装仓储层 |
| `app.py` 线程逻辑 | `app/workers/analysis_worker.py` | 改为队列消费任务 |
| `app.py` StandardizedLLMClient | `app/services/llm_service.py` | 统一 provider 输出结构 |
| `json2ziwei/api.py` | `app/services/ziwei_service.py` | 合并并补超时/异常处理 |
| `json2ziwei/convert.py` | `app/services/ziwei_service.py` | 合并 |
| `llmana/*` | `app/llm_providers/*` | 统一继承 `BaseLLMProvider` |
| `token_ana/deepseek_tokenizer.py` | `app/utils/tokenizer.py` | 迁移并补单元测试 |
| `src/index.js` | `iztro_service/index.js` | 保持不变 |

---

## 五、前端重构方案

### 5.1 技术栈

| 技术 | 用途 |
|------|------|
| React 19 | UI 框架 |
| Vite | 构建工具 |
| TypeScript | 类型安全 |
| React Router | 路由管理 |
| Axios | HTTP 请求 |
| react-markdown | Markdown 渲染 |
| TailwindCSS | 样式框架（水墨主题） |

### 5.2 目录结构

```
frontend/
├── public/
│   ├── textures/
│   └── fonts/
├── src/
│   ├── api/
│   │   └── index.ts
│   ├── types/
│   │   └── index.ts
│   ├── components/
│   │   ├── Layout.tsx
│   │   ├── InkCard.tsx
│   │   ├── InkButton.tsx
│   │   ├── InkDivider.tsx
│   │   ├── LoadingAnimation.tsx
│   │   └── MarkdownRenderer.tsx
│   ├── pages/
│   │   ├── Home.tsx
│   │   ├── Loading.tsx
│   │   ├── Result.tsx
│   │   ├── Detail.tsx
│   │   └── History.tsx
│   ├── hooks/
│   │   └── useAnalysis.ts
│   ├── styles/
│   │   └── ink-theme.css
│   ├── App.tsx
│   └── main.tsx
├── package.json
└── vite.config.ts
```

### 5.3 页面与路由

| 路由 | 页面 | 说明 |
|------|------|------|
| `/` | Home.tsx | 生辰信息输入 |
| `/loading/:taskId` | Loading.tsx | 查询任务进度 |
| `/result/:id` | Result.tsx | 三项分析总览 |
| `/result/:id/:type` | Detail.tsx | 单项分析详情 |
| `/history` | History.tsx | 历史记录 |

### 5.4 关键页面行为

#### Home.tsx

- 表单提交调用 `POST /api/analyze`。
- `200 cache_hit`：直接跳转 `/result/:id`。
- `202 accepted`：跳转 `/loading/:taskId`。

#### Loading.tsx

- 每 2 秒轮询 `GET /api/task/<taskId>`。
- `status=succeeded`：跳转 `/result/:resultId`。
- `status=failed`：展示错误信息与“重试”按钮。
- 本地保存 `task_id`，支持刷新恢复。

#### Result.tsx / Detail.tsx

- 使用 `GET /api/result/<id>` 拉取结构化数据。
- 卡片展示 `execution_time`、`token_count`、`provider`、`model`。
- 支持一键下载全量或单项 Markdown。

### 5.5 核心类型定义 `types/index.ts`

```typescript
type TaskStatus = 'queued' | 'running' | 'succeeded' | 'failed' | 'cancelled';

interface BirthInfo {
  date: string;
  timezone: number;
  gender: '男' | '女';
  calendar: 'solar' | 'lunar';
}

interface AnalyzeAcceptedData {
  task_id: string;
  status: TaskStatus;
  poll_after_ms: number;
  hit_cache: boolean;
}

interface TaskData {
  task_id: string;
  status: TaskStatus;
  progress: number;
  step: string;
  result_id: number | null;
  retry_count: number;
  error: {
    code: string;
    message: string;
    retryable: boolean;
  } | null;
}

interface AnalysisItem {
  content: string;
  execution_time: number;
  token_count: number;
  input_tokens: number;
  output_tokens: number;
}

interface AnalysisResult {
  id: number;
  birth_info: BirthInfo;
  provider: string;
  model: string;
  prompt_version: string;
  text_description: string;
  analysis: {
    marriage_path: AnalysisItem;
    challenges: AnalysisItem;
    partner_character: AnalysisItem;
  };
  total_execution_time: number;
  total_token_count: number;
  created_at: string;
}

interface ApiResponse<T> {
  code: number | string;
  message: string;
  data?: T;
  request_id: string;
}
```

### 5.6 API 请求封装 `api/index.ts`

```typescript
import axios from 'axios';

const api = axios.create({ baseURL: '/api' });

export const submitAnalysis = (birthInfo: BirthInfo) =>
  api.post<ApiResponse<AnalyzeAcceptedData | { result_id: number; hit_cache: true }>>('/analyze', birthInfo);

export const getTask = (taskId: string) =>
  api.get<ApiResponse<TaskData>>(`/task/${taskId}`);

export const retryTask = (taskId: string) =>
  api.post<ApiResponse<{ task_id: string }>>(`/task/${taskId}/retry`);

export const cancelTask = (taskId: string) =>
  api.post<ApiResponse<{ task_id: string }>>(`/task/${taskId}/cancel`);

export const getResult = (id: number) =>
  api.get<ApiResponse<AnalysisResult>>(`/result/${id}`);

export const getHistory = (page = 1, pageSize = 20) =>
  api.get(`/history?page=${page}&page_size=${pageSize}`);

export const exportReport = (id: number, scope = 'full') =>
  api.get(`/export/${id}?scope=${scope}`, { responseType: 'blob' });
```

---

## 六、开发与部署

### 6.1 开发环境

同时启动五个服务：

| 服务 | 端口 | 启动命令 |
|------|------|----------|
| React 前端 | 5173 | `cd frontend && pnpm dev` |
| Flask API | 5000 | `cd backend && python run.py` |
| RQ Worker | - | `cd backend && python worker.py` |
| Redis | 6379 | `redis-server` |
| iztro 服务 | 3000 | `cd backend/iztro_service && node index.js` |

Vite 代理：

```typescript
// vite.config.ts
export default defineConfig({
  server: {
    proxy: {
      '/api': 'http://localhost:5000'
    }
  }
});
```

### 6.2 生产部署

```
                     ┌──────────────────────────┐
  用户 ────────────►  │          Nginx            │
                     │ /       -> frontend/dist  │
                     │ /api/*  -> Flask API      │
                     └─────────────┬─────────────┘
                                   │
                     ┌─────────────▼─────────────┐
                     │         Flask API          │
                     └───────┬───────────┬───────┘
                             │           │
                    ┌────────▼───┐   ┌──▼────────────┐
                    │   Redis    │   │ iztro Service │
                    └────────┬───┘   └───────────────┘
                             │
                    ┌────────▼────────┐
                    │   RQ Workers     │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │ SQLite / PGSQL   │
                    └──────────────────┘
```

建议：

- 开发期可用 SQLite；生产优先 PostgreSQL。
- API 与 Worker 独立扩容，防止互相抢资源。
- iztro 仅内网访问，不对公网暴露。

---

## 七、重构步骤（含迁移与回滚）

### 第一阶段：后端基础重构

| 步骤 | 内容 | 依赖 |
|------|------|------|
| 1.1 | 创建 `backend/` 分层目录 | 无 |
| 1.2 | 迁移 `iztro_service/` | 无 |
| 1.3 | 新建 DB schema（tasks/results/items） | 无 |
| 1.4 | 建立 `response.py`、错误码、`request_id` 中间件 | 1.1 |
| 1.5 | 迁移 `llm_providers/` 并统一抽象返回 | 1.1 |
| 1.6 | 实现 `ziwei_service.py`、`llm_service.py`、`analysis_service.py` | 1.2,1.5 |

### 第二阶段：异步任务化

| 步骤 | 内容 | 依赖 |
|------|------|------|
| 2.1 | 接入 Redis + RQ，新增 `worker.py` | 1.x |
| 2.2 | 实现 `POST /api/analyze`（202 返回） | 2.1 |
| 2.3 | 实现 `GET /api/task/<id>` / cancel / retry | 2.1 |
| 2.4 | 实现缓存命中短路（200 直接返回 `result_id`） | 2.2 |
| 2.5 | API 契约测试 + 集成测试 | 2.2,2.3 |

### 第三阶段：前端接入

| 步骤 | 内容 | 依赖 |
|------|------|------|
| 3.1 | 初始化 React + Vite + TypeScript | 无 |
| 3.2 | 实现 API 层与类型定义 | 2.x |
| 3.3 | Home 页面（提交并分流到 cache/result 或 task/loading） | 3.2 |
| 3.4 | Loading 页面（轮询、错误处理、断点恢复） | 3.2 |
| 3.5 | Result / Detail / History 页面 | 3.2 |

### 第四阶段：质量与运维

| 步骤 | 内容 |
|------|------|
| 4.1 | 接入结构化日志、监控指标、健康检查 |
| 4.2 | 加入限流、参数校验、CORS 白名单 |
| 4.3 | 压测（并发提交、失败重试、缓存命中） |
| 4.4 | 灰度发布 + 回滚演练 |

### 第五阶段：切换与清理

| 步骤 | 内容 |
|------|------|
| 5.1 | 开启新前端流量，保留旧页面只读一段时间 |
| 5.2 | 验证历史数据可查询与导出 |
| 5.3 | 删除旧 `templates/`、`static/`、根目录 `app.py` |
| 5.4 | 更新 README 和部署脚本 |

### 回滚策略

- 回滚维度：前端静态资源、后端 API 版本、数据库迁移脚本。
- 保留旧接口兼容窗口（建议 1 个发布周期）。
- 数据迁移采用“新增表 + 回填 + 双写开关”，避免不可逆变更。

---

## 八、测试与验收清单

### 8.1 测试矩阵

| 类型 | 覆盖内容 |
|------|----------|
| 单元测试 | 服务层逻辑、Provider 适配、错误码映射 |
| 契约测试 | `analyze/task/result/history/export` JSON 结构 |
| 集成测试 | API + Redis + Worker + DB 全链路 |
| E2E 测试 | 提交分析 -> 轮询 -> 查看结果 -> 导出 |
| 压测 | 并发提交、队列堆积、失败重试 |

### 8.2 通过标准

- `POST /api/analyze` P95 响应 < 300ms。
- 长任务执行期间 API 无阻塞、无超时雪崩。
- 失败任务可重试且结果一致。
- 缓存命中时不重复调用 LLM。
- 发布失败可在 5 分钟内回滚。

---

## 九、最终项目结构

```
DeepSeek-Oracle/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── api/
│   │   ├── services/
│   │   ├── workers/
│   │   ├── models/
│   │   ├── llm_providers/
│   │   ├── schemas/
│   │   └── utils/
│   ├── iztro_service/
│   ├── migrations/
│   ├── requirements.txt
│   ├── run.py
│   └── worker.py
├── frontend/
│   ├── src/
│   │   ├── api/
│   │   ├── types/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── hooks/
│   │   ├── styles/
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── package.json
│   └── vite.config.ts
└── docs/
    ├── PRD.md
    └── REFACTOR.md
```
