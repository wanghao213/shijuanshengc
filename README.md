# MathPaperForge - 数学试卷智能生成系统

基于多 Agent 管线的数学试卷智能生成平台，支持题库管理、OCR 识别、AI 出题、LaTeX 渲染与多格式导出。

---

> **功能截图占位区**
>
> - **首页仪表盘**: 统计概览，展示题目数量、近期生成任务、知识点覆盖率
> - **题库管理页**: 表格视图，支持筛选、排序、批量操作，右侧详情抽屉
> - **OCR 识别页**: 左侧上传区 + 右侧识别结果预览，支持对比编辑
> - **试卷生成页**: 左侧参数配置面板（题型/知识点/难度），右侧实时进度流
> - **试卷预览页**: LaTeX 渲染的试卷预览，工具栏支持 PDF/DOCX/LaTeX 导出
> - **知识点树页**: 可展开的树形结构，支持拖拽排序和批量编辑

---

## 技术架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        Nginx (前端容器)                          │
│                  静态资源 + API 反向代理 + WS 代理                 │
└────────────┬──────────────────────────────────┬─────────────────┘
             │  /api/*                          │  /api/v1/generation/ws/*
             ▼                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FastAPI Backend (Python 3.11)                 │
│                                                                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────────┐  │
│  │  API层    │  │ Services │  │  Tasks   │  │   Agents       │  │
│  │ (路由)    │→│ (业务逻辑)│→│(后台任务) │  │ (多Agent管线)  │  │
│  └──────────┘  └──────────┘  └──────────┘  └────────────────┘  │
│       │              │              │               │           │
│       ▼              ▼              ▼               ▼           │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              数据层 & 外部服务                              │   │
│  │                                                          │   │
│  │  ┌──────────────┐  ┌─────────┐  ┌─────────────────────┐ │   │
│  │  │ PostgreSQL   │  │  Redis  │  │  LiteLLM (多模型)    │ │   │
│  │  │ + pgvector   │  │ (缓存)  │  │  (LLM Gateway)      │ │   │
│  │  │ (向量检索)    │  │         │  │                     │ │   │
│  │  └──────────────┘  └─────────┘  └─────────────────────┘ │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘

                    ┌─────────────────────────┐
                    │      React + Ant Design  │
                    │      (Vite / pnpm)       │
                    └─────────────────────────┘
```

**数据流**: 前端 -> Nginx -> FastAPI (REST + WebSocket) -> PostgreSQL / Redis / LiteLLM

---

## 功能特性

- **题库管理** - 题目 CRUD、批量导入、版本管理、多维度筛选
- **OCR 试卷识别** - MinerU OCR 提取 + LLM 智能清洗，支持图片/PDF 上传
- **AI 智能出题** - 多 Agent 管线：Planner -> Retriever -> Generator -> Validator -> Assembler
- **试卷生成与预览** - LaTeX 实时渲染，WebSocket 推送生成进度
- **多格式导出** - PDF / DOCX / LaTeX 三种格式一键导出
- **知识点树管理** - 树形结构管理数学知识点，支持拖拽排序
- **向量语义检索** - pgvector 向量存储 + RRF 混合检索（全文 + 语义）

---

## 快速开始

### 环境要求

| 方式 | 要求 |
|------|------|
| Docker 部署 | Docker & Docker Compose |
| 本地开发 | Python 3.11+, Node.js 20+, PostgreSQL 16+ (pgvector), Redis 7+ |

### 一键启动

```bash
# 克隆项目
git clone <repo-url>
cd mathpaperforge

# 复制环境变量
cp .env.example .env
# 编辑 .env 填入 LLM API Key 等必要配置

# Docker Compose 启动（基础设施 + 应用）
make dev
# 或
docker-compose up -d
```

启动后访问:
- 前端: http://localhost:5173
- 后端 API: http://localhost:8000
- Swagger 文档: http://localhost:8000/docs

### 本地开发

```bash
# 后端
cd backend
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000

# 前端
cd frontend
pnpm install
pnpm dev
```

---

## 环境变量说明

在项目根目录创建 `.env` 文件，参考以下配置:

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `DATABASE_URL` | PostgreSQL 连接字符串 | `postgresql+asyncpg://postgres:postgres@localhost:5432/mathpaperforge` |
| `REDIS_URL` | Redis 连接地址 | `redis://localhost:6379/0` |
| `SECRET_KEY` | JWT 签名密钥 | (必填) |
| `LLM_API_KEY` | LiteLLM / OpenAI 兼容 API Key | (必填) |
| `LLM_BASE_URL` | LiteLLM Gateway 地址 | `https://api.openai.com/v1` |
| `LLM_MODEL` | 默认使用的模型 | `gpt-4o` |
| `EMBEDDING_MODEL` | 向量嵌入模型 | `text-embedding-3-small` |
| `MINERU_API_KEY` | MinerU OCR 服务 API Key | (可选) |
| `UPLOAD_DIR` | 上传文件存储路径 | `./uploads` |
| `EXPORT_DIR` | 导出文件存储路径 | `./exports` |
| `CORS_ORIGINS` | 允许的跨域来源 | `http://localhost:5173` |
| `POSTGRES_USER` | PostgreSQL 用户名 | `postgres` |
| `POSTGRES_PASSWORD` | PostgreSQL 密码 | `postgres` |
| `POSTGRES_DB` | PostgreSQL 数据库名 | `mathpaperforge` |

---

## API 文档

启动后访问 http://localhost:8000/docs 查看 Swagger UI

### 主要 API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/v1/questions/` | 题目列表（分页、筛选） |
| `POST` | `/api/v1/questions/` | 创建题目 |
| `POST` | `/api/v1/questions/batch-import` | 批量导入题目 |
| `GET` | `/api/v1/knowledge/tree` | 获取知识点树 |
| `POST` | `/api/v1/generation/generate` | 发起试卷生成任务 |
| `WS` | `/api/v1/generation/ws/{task_id}` | WebSocket 实时进度 |
| `POST` | `/api/v1/papers/{id}/export` | 导出试卷（PDF/DOCX/LaTeX） |
| `POST` | `/api/v1/ocr/process` | OCR 文本识别与清洗 |

---

## 架构演进说明

### V1 -> V2 演进

| 维度 | V1 | V2 |
|------|----|----|
| 架构 | 单体 FastAPI + PostgreSQL | 多 Agent 管线 + 向量检索 |
| 出题方式 | 规则匹配 | 5 Agent 协作管线 |
| 检索 | SQL 全文搜索 | 全文 + 向量语义混合检索 (RRF) |
| 进度反馈 | 轮询 | WebSocket 实时推送 |
| 试卷识别 | 无 | MinerU OCR + LLM 清洗管线 |
| 题目版本 | 无 | 自动版本追踪 |

---

## 技术亮点（面试重点）

1. **多 Agent 管线架构**: 5 个专职 Agent（Planner / Retriever / Generator / Validator / Assembler）协作生成试卷，每个 Agent 职责单一、可独立替换和测试
2. **RAG 混合检索**: PostgreSQL 全文检索 + pgvector 向量语义检索通过 RRF（Reciprocal Rank Fusion）算法融合，兼顾精确匹配与语义理解
3. **实时进度推送**: WebSocket + FastAPI BackgroundTasks 实现生成过程可视化，前端实时展示每个 Agent 的执行状态
4. **LaTeX 编译管线**: 两遍 XeLaTeX 编译流程，支持交叉引用和自定义模板
5. **OCR + LLM 清洗**: MinerU OCR 提取原始文本 -> LLM 纠错与格式修复 -> 结构化 JSON 提取的三步管线
6. **版本化题目管理**: 基于 SQLAlchemy 事件的自动版本追踪，支持内容回溯与差异对比

---

## Makefile 命令

| 命令 | 说明 |
|------|------|
| `make dev` | 启动完整开发环境（Docker 基础设施 + 本地应用） |
| `make dev-backend` | 仅启动后端开发服务器 |
| `make dev-frontend` | 仅启动前端开发服务器 |
| `make migrate` | 执行数据库迁移（alembic upgrade head） |
| `make migrate-create MSG="描述"` | 创建新的数据库迁移 |
| `make seed` | 填充种子数据（知识点 + 题目 + 模板） |
| `make db-reset` | 重置数据库（降级 + 升级 + 填充种子） |
| `make test` | 运行全部测试（后端 + 前端） |
| `make test-backend` | 运行后端测试 |
| `make test-frontend` | 运行前端测试 |
| `make coverage` | 生成后端测试覆盖率报告 |
| `make lint` | 代码检查（Ruff + mypy + ESLint + tsc） |
| `make format` | 代码格式化 |
| `make build` | 构建生产环境 Docker 镜像 |

---

## License

MIT
