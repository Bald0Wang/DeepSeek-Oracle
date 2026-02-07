# DeepSeek-Oracle

基于紫微斗数与大语言模型的命盘分析系统。

当前版本已完成前后端分离，原 Flask 模板单体已下线。

## 架构

- `backend/`：Flask API + Redis + RQ Worker（异步任务）
- `frontend/`：React + Vite + TypeScript（独立前端）
- `backend/iztro_service/`：Node 星盘服务（后端内部依赖）

## 主要能力

- 阳历/阴历命盘生成
- 异步分析任务（提交、轮询、重试、取消）
- 三类分析：婚姻道路、困难挑战、伴侣性格
- 历史记录查询与 Markdown 报告导出
- 缓存命中与任务复用（避免重复推演）

## 环境要求

- Python 3.10+
- Node.js 18+
- Redis 6+

## 快速启动（开发环境）

1) 启动 Redis

```bash
redis-server
```

2) 启动后端 API

```bash
cd backend
py -3 -m pip install -r requirements.txt
copy .env.example .env
py -3 run.py
```

3) 启动 Worker

```bash
cd backend
py -3 worker.py
```

4) 启动 iztro 服务

```bash
cd backend/iztro_service
npm install
npm start
```

5) 启动前端

```bash
cd frontend
npm install
npm run dev
```

前端默认地址：`http://localhost:5173`

## 旧数据迁移（可选）

如果你之前使用过旧单体版本并保留了旧 `data.db`，可执行：

```bash
py -3 backend/scripts/migrate_legacy_results.py --legacy-db data.db --new-db backend/data.db
```

## 目录结构

```text
DeepSeek-Oracle/
├── backend/
│   ├── app/
│   ├── iztro_service/
│   ├── migrations/
│   ├── scripts/
│   ├── run.py
│   └── worker.py
├── frontend/
│   ├── src/
│   ├── package.json
│   └── vite.config.ts
└── docs/
    └── REFACTOR.md
```

## License

MIT
