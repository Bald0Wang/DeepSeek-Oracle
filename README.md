# DeepSeek-Oracle

基于紫微斗数与大语言模型的命盘分析系统。

当前版本已完成前后端分离，原 Flask 模板单体已下线。

## 架构

- `backend/`：Flask API + Redis + RQ Worker（异步任务）
- `frontend/`：React + Vite + TypeScript（独立前端）
- `izthon/`：Python 星盘计算库（后端直接调用，不再依赖 Node 星盘 API）

## 主要能力

- 阳历/阴历命盘生成
- 异步分析任务（提交、轮询、重试、取消）
- 三类分析：婚姻道路、困难挑战、伴侣性格
- 多智能体咨询编排（安全审查 + 长短线路由 + 统一答复）
- 历史记录查询与 Markdown 报告导出
- 缓存命中与任务复用（避免重复推演）
- 邮箱验证码注册与找回密码（SMTP）

## 新增接口（多智能体咨询）

- `POST /api/oracle/chat`

请求体示例：

```json
{
  "user_query": "我最近想换工作，想看未来半年走势和本周行动",
  "selected_school": "east",
  "enabled_schools": ["ziwei", "meihua", "actionizer", "philosophy"],
  "user_profile_summary": "互联网从业者，近期压力较大",
  "conversation_history_summary": "过去两次咨询都围绕职业决策"
}
```

返回结构：

- `answer_text`
- `follow_up_questions`
- `action_items`
- `safety_disclaimer_level`
- `trace`

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
# 如未安装 izthon，可在 .env 中设置 IZTHON_SRC_PATH 指向本地 izthon/src
py -3 run.py
```

3) 启动 Worker

```bash
cd backend
py -3 worker.py
```

4) 启动前端

```bash
cd frontend
npm install
npm run dev
```

前端默认地址：`http://localhost:5173`

## Docker 一键启动

项目已提供完整容器编排：`frontend + backend + worker + redis`。

### 推荐：脚本一键启动（Windows / PowerShell）

```bash
.\docker.ps1 up
```

可选参数：

- `.\docker.ps1 up -NoBuild`：跳过镜像重建，快速拉起
- `.\docker.ps1 restart`：重启全部容器
- `.\docker.ps1 logs`：查看实时日志
- `.\docker.ps1 down`：停止服务

双击启动（Windows）：

```bash
start-docker.bat
```

脚本会自动：

1) 若缺少 `.env.docker`，从 `.env.docker.example` 生成  
2) 校验 `IZTHON_SRC_PATH_HOST` 是否存在  
3) 执行 `docker compose up -d --build`  
4) 等待后端健康检查通过并输出访问地址

### 邮箱 SMTP 配置（QQ邮箱）

已支持以下认证流程：

- `POST /api/auth/admin/send-code`：向特殊管理员邮箱发送后台登录验证码
- `POST /api/auth/admin/code-login`：特殊管理员邮箱 + 验证码直接登录后台
- `POST /api/auth/register/send-code`：发送注册验证码
- `POST /api/auth/register`：邮箱 + 验证码 + 密码注册
- `POST /api/auth/password/forgot`：发送找回密码验证码
- `POST /api/auth/password/reset`：验证码重置密码

需要在 `.env` 或 `.env.docker` 中配置：

- `EMAIL_VERIFY_REQUIRED=true`
- `EMAIL_CODE_EXPIRE_MINUTES=10`
- `SPECIAL_ADMIN_EMAIL=bald0wang@qq.com`
- `SMTP_HOST=smtp.qq.com`
- `SMTP_PORT=465`
- `SMTP_USE_SSL=true`
- `SMTP_USERNAME=<你的邮箱>`
- `SMTP_PASSWORD=<QQ邮箱授权码>`
- `SMTP_FROM_EMAIL=<发件邮箱>`
- `SMTP_FROM_NAME=DeepSeek Oracle`

### 手动方式（通用）

1) 准备 Docker 环境变量

```bash
cp .env.docker.example .env.docker
```

关键变量：

- `IZTHON_SRC_PATH_HOST`：本地 `izthon/src` 路径（紫微计算依赖，默认 `../izthon/src`）
- `FRONTEND_PORT`：前端端口，默认 `8080`
- `BACKEND_PORT`：后端端口，默认 `5000`
- `LLM_PROVIDER`：默认 `volcano`（Ark）

2) 启动服务

```bash
docker compose --env-file .env.docker up -d --build
```

3) 访问与检查

- 前端：`http://localhost:8080`
- 后端健康检查：`http://localhost:5000/healthz`
- 查看日志：`docker compose logs -f`

4) 停止服务

```bash
docker compose --env-file .env.docker down
```

## 开发辅助 Subagent（安全审查）

已新增一个开发后安全审查 subagent：

- 路径：`.codex/skills/post-dev-security-review/`
- 主配置：`.codex/skills/post-dev-security-review/SKILL.md`
- 检查清单：`.codex/skills/post-dev-security-review/references/deepseek-oracle-security-checklist.md`

建议在每次功能开发完成后使用类似请求触发：

- `请用 post-dev-security-review 对这次改动做安全审查`
- `请基于最近 git diff 给出安全问题和优化建议`

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
