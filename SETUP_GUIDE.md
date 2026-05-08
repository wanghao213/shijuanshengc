# MathPaperForge 项目启动指南

> 数学试卷智能生成系统 — 从环境搭建到完整运行的详细流程

---

## 目录

- [一、系统要求](#一系统要求)
- [二、环境准备](#二环境准备)
- [三、项目配置](#三项目配置)
- [四、启动方式](#四启动方式)
  - [方式 A：本地开发（推荐）](#方式-a本地开发推荐)
  - [方式 B：Docker Compose](#方式-bdocker-compose)
- [五、数据库初始化](#五数据库初始化)
- [六、验证运行](#六验证运行)
- [七、开发工作流](#七开发工作流)
- [八、常用命令速查](#八常用命令速查)
- [九、故障排除](#九故障排除)
- [十、生产部署](#十生产部署)

---

## 一、系统要求

### 必需软件

| 软件 | 最低版本 | 说明 |
|------|---------|------|
| **Python** | 3.11+ | 后端运行时 |
| **Node.js** | 20+ | 前端构建 |
| **pnpm** | 8+ | 前端包管理器 |
| **Docker** | 24+ | 运行 PostgreSQL 和 Redis |
| **Docker Compose** | 2.20+ | 编排服务 |
| **Git** | 2.30+ | 版本管理 |

### 可选软件

| 软件 | 用途 | 说明 |
|------|------|------|
| **TeX Live** | PDF 导出 | 需要 `xelatex` + `ctex` 宏包 |
| **uv** | Python 包管理 | 比 pip 更快（推荐） |
| **Make** | 命令快捷方式 | Windows 需安装 `make` 或使用 Git Bash |

### API Key（至少需要一个）

| 服务 | 环境变量 | 用途 |
|------|---------|------|
| Anthropic | `ANTHROPIC_API_KEY` | Claude 模型（默认主模型） |
| OpenAI | `OPENAI_API_KEY` | GPT 模型 + Embedding |
| DeepSeek | `DEEPSEEK_API_KEY` | DeepSeek 模型（低成本备选） |

> **注意**：系统通过 LiteLLM 网关统一调用，至少配置一个 API Key 即可运行。推荐配置 Anthropic（主模型）+ OpenAI（Embedding）。

---

## 二、环境准备

### 2.1 安装 Python 3.11+

**Windows：**
```bash
# 方式 1：从官网下载
# 访问 https://www.python.org/downloads/ 下载 3.11+ 安装包

# 方式 2：使用 winget
winget install Python.Python.3.11

# 验证
python --version   # 应显示 Python 3.11.x
```

**macOS：**
```bash
# 使用 Homebrew
brew install python@3.11
```

**Linux (Ubuntu/Debian)：**
```bash
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update
sudo apt install python3.11 python3.11-venv python3.11-dev
```

### 2.2 安装 Node.js 和 pnpm

```bash
# 安装 Node.js 20+（从 https://nodejs.org 或使用 nvm）
# Windows:
winget install OpenJS.NodeJS.LTS

# 安装 pnpm
npm install -g pnpm

# 验证
node --version   # 应显示 v20.x.x
pnpm --version   # 应显示 8.x.x 或更高
```

### 2.3 安装 Docker Desktop

**Windows/macOS：**
- 下载安装 [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- 安装后确保 Docker 正在运行

**Linux：**
```bash
# 安装 Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
# 重新登录终端

# 安装 Docker Compose（如果未随 Docker 安装）
sudo apt install docker-compose-plugin
```

**验证 Docker：**
```bash
docker --version        # Docker version 24.x.x
docker compose version  # Docker Compose version 2.x.x
```

### 2.4 安装 uv（推荐，可选）

```bash
# uv 是超快的 Python 包管理器，替代 pip
pip install uv
# 或
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2.5 安装 TeX Live（可选，用于 PDF 导出）

**Windows：**
- 安装 [MiKTeX](https://miktex.org/download) 或 [TeX Live](https://www.tug.org/texlive/)
- 确保 `xelatex` 命令可用

**macOS：**
```bash
brew install --cask mactex
```

**Linux：**
```bash
sudo apt install texlive-xetex texlive-lang-chinese texlive-latex-extra
```

**验证：**
```bash
xelatex --version   # 应显示版本信息
```

---

## 三、项目配置

### 3.1 克隆/进入项目

```bash
cd C:\Users\王浩\Desktop\试卷生成\mathpaperforge
```

### 3.2 创建环境变量文件

```bash
# 复制模板
cp .env.example .env
```

### 3.3 编辑 .env 文件

用文本编辑器打开 `.env`，修改以下关键配置：

```env
# ============================================================
# 必须修改的配置
# ============================================================

# AI API Keys（至少配置一个）
ANTHROPIC_API_KEY=sk-ant-api03-xxxxxxxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxx
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxx

# 应用密钥（改为随机字符串）
APP_SECRET_KEY=your-random-secret-key-here-at-least-32-chars

# ============================================================
# 一般无需修改的配置（使用 Docker 时保持默认）
# ============================================================

# 数据库（Docker 启动的 PostgreSQL 默认就是这个地址）
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/mathpaperforge
DATABASE_URL_SYNC=postgresql://postgres:postgres@localhost:5432/mathpaperforge

# Redis
REDIS_URL=redis://localhost:6379/0

# 默认模型
DEFAULT_CHAT_MODEL=claude-sonnet-4-20250514
DEFAULT_EMBEDDING_MODEL=text-embedding-3-small
DEFAULT_FAST_MODEL=deepseek-chat

# 并发控制
LITELLM_MAX_CONCURRENT=10
LITELLM_REQUEST_TIMEOUT=60

# 应用配置
APP_ENV=development
APP_DEBUG=false
APP_LOG_LEVEL=INFO

# 文件存储
UPLOAD_DIR=./uploads
EXPORT_DIR=./exports

# LaTeX 编译器
LATEX_COMPILER=xelatex
LATEX_TIMEOUT=30

# OCR（MinerU，可选）
MINERU_ENABLED=false
MINERU_MODEL_DIR=./models/mineru

# 前端（开发时无需修改）
VITE_API_BASE_URL=http://localhost:8000
VITE_WS_BASE_URL=ws://localhost:8000
```

### 3.4 创建必要目录

```bash
# 在 mathpaperforge 根目录下
mkdir -p uploads exports
```

---

## 四、启动方式

### 方式 A：本地开发（推荐）

适合日常开发，代码修改后自动热重载。

#### 步骤 1：启动基础设施（PostgreSQL + Redis）

```bash
# 在 mathpaperforge 根目录
docker compose up -d postgres redis
```

验证服务启动：
```bash
# 检查容器状态
docker compose ps

# 应该看到：
# mathpaperforge-postgres   running   0.0.0.0:5432->5432/tcp
# mathpaperforge-redis      running   0.0.0.0:6379->6379/tcp

# 测试 PostgreSQL 连接
docker compose exec postgres psql -U postgres -d mathpaperforge -c "SELECT 1;"

# 测试 Redis 连接
docker compose exec redis redis-cli ping
# 应返回 PONG
```

#### 步骤 2：安装后端依赖

```bash
cd backend

# 方式 1：使用 uv（推荐，更快）
uv sync

# 方式 2：使用 pip
pip install -e ".[dev]"

# 验证
python -c "import fastapi; print(fastapi.__version__)"
```

#### 步骤 3：运行数据库迁移

```bash
cd backend

# 创建数据库表 + 索引 + 扩展
alembic upgrade head
```

预期输出：
```
INFO  [alembic] Running upgrade  -> 001_initial_schema, Initial schema
```

#### 步骤 4：导入种子数据

```bash
cd backend

# 导入知识点树（约 200 个节点）
python -m scripts.seed_knowledge

# 导入示例题目（约 50 道）
python -m scripts.seed_questions

# 创建试卷模板（3 个）
python -m scripts.seed_templates
```

或使用 Makefile 一键执行：
```bash
make seed
```

#### 步骤 5：启动后端

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

或使用 Makefile：
```bash
make dev-backend
```

预期输出：
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

#### 步骤 6：启动前端

**新开一个终端窗口：**
```bash
cd frontend

# 安装依赖
pnpm install

# 启动开发服务器
pnpm dev
```

或使用 Makefile：
```bash
make dev-frontend
```

预期输出：
```
  VITE v5.x.x  ready in xxx ms

  ➜  Local:   http://localhost:5173/
  ➜  Network: http://192.168.x.x:5173/
```

#### 步骤 7：访问应用

| 服务 | 地址 | 说明 |
|------|------|------|
| **前端页面** | http://localhost:5173 | React 应用主界面 |
| **后端 API** | http://localhost:8000 | FastAPI 服务 |
| **API 文档** | http://localhost:8000/docs | Swagger UI 交互文档 |
| **健康检查** | http://localhost:8000/health | 服务状态 |

---

### 方式 B：Docker Compose

适合一次性启动所有服务，但不支持代码热重载。

```bash
# 在 mathpaperforge 根目录

# 构建并启动所有服务
docker compose up -d

# 查看日志
docker compose logs -f

# 查看状态
docker compose ps
```

> **注意**：Docker 方式首次启动需要构建镜像，可能需要 5-10 分钟。

---

## 五、数据库初始化

### 5.1 迁移管理

```bash
cd backend

# 查看当前迁移状态
alembic current

# 升级到最新
alembic upgrade head

# 回滚一个版本
alembic downgrade -1

# 回滚到初始状态
alembic downgrade base

# 创建新迁移（修改模型后）
alembic revision --autogenerate -m "描述信息"
```

### 5.2 种子数据说明

| 脚本 | 内容 | 数量 |
|------|------|------|
| `seed_knowledge.py` | 知识点树（小学→初中→高中） | ~200 个节点 |
| `seed_questions.py` | 示例数学题（含 LaTeX、答案、解题步骤） | ~50 道 |
| `seed_templates.py` | 试卷模板（含结构化 JSON） | 3 个 |

### 5.3 完全重置数据库

```bash
# 使用 Makefile
make db-reset

# 或手动执行
cd backend
alembic downgrade base
alembic upgrade head
python -m scripts.seed_knowledge
python -m scripts.seed_questions
python -m scripts.seed_templates
```

---

## 六、验证运行

### 6.1 健康检查

```bash
curl http://localhost:8000/health
```

预期响应：
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "database": "connected",
  "redis": "connected"
}
```

### 6.2 验证 API

```bash
# 获取知识点树
curl http://localhost:8000/api/v1/knowledge/tree

# 获取题目列表
curl http://localhost:8000/api/v1/questions/

# 获取模板列表
curl http://localhost:8000/api/v1/templates/

# 获取统计信息
curl http://localhost:8000/api/v1/questions/stats
```

### 6.3 验证前端

1. 打开浏览器访问 http://localhost:5173
2. 应看到 Dashboard 仪表盘页面
3. 点击左侧菜单，检查各页面是否正常加载
4. 在「题库管理」页面应能看到种子数据中的题目

### 6.4 运行测试

```bash
# 后端测试
make test-backend

# 或手动
cd backend && pytest -v

# 查看覆盖率
make coverage
```

---

## 七、开发工作流

### 7.1 日常开发流程

```
1. 启动基础设施
   docker compose up -d postgres redis

2. 启动后端（终端 1）
   make dev-backend

3. 启动前端（终端 2）
   make dev-frontend

4. 修改代码 → 自动热重载 → 浏览器刷新查看效果

5. 提交前检查
   make lint        # 代码规范检查
   make test        # 运行测试
```

### 7.2 修改数据库模型后

```bash
cd backend

# 1. 修改 app/models/ 下的模型文件
# 2. 生成迁移
alembic revision --autogenerate -m "描述变更"

# 3. 检查生成的迁移文件（在 alembic/versions/ 下）
# 4. 应用迁移
alembic upgrade head
```

### 7.3 添加新的 API 端点

```
1. 在 app/schemas/ 中定义请求/响应 Schema
2. 在 app/services/ 中实现业务逻辑
3. 在 app/api/v1/endpoints/ 中创建路由
4. 在 app/api/v1/router.py 中注册路由
5. 编写测试
```

### 7.4 代码规范

```bash
# Python 格式化
make format

# Python 检查
make lint-backend

# TypeScript 检查
make lint-frontend
```

---

## 八、常用命令速查

### Makefile 命令

| 命令 | 说明 |
|------|------|
| `make help` | 显示所有可用命令 |
| `make dev-backend` | 启动后端开发服务器 |
| `make dev-frontend` | 启动前端开发服务器 |
| `make install` | 安装所有依赖 |
| `make migrate` | 运行数据库迁移 |
| `make seed` | 导入种子数据 |
| `make db-reset` | 重置数据库 |
| `make test` | 运行所有测试 |
| `make test-backend` | 运行后端测试 |
| `make coverage` | 生成测试覆盖率报告 |
| `make lint` | 运行代码规范检查 |
| `make format` | 自动格式化代码 |
| `make docker-up` | 启动 Docker 服务 |
| `make docker-down` | 停止 Docker 服务 |
| `make build` | 构建生产镜像 |
| `make prod` | 启动生产环境 |
| `make clean` | 清理构建缓存 |

### Docker 命令

| 命令 | 说明 |
|------|------|
| `docker compose up -d postgres redis` | 仅启动基础设施 |
| `docker compose up -d` | 启动所有服务 |
| `docker compose down` | 停止所有服务 |
| `docker compose ps` | 查看服务状态 |
| `docker compose logs -f` | 查看实时日志 |
| `docker compose logs -f backend` | 查看后端日志 |
| `docker compose exec postgres psql -U postgres` | 进入 PostgreSQL |

### Alembic 命令

| 命令 | 说明 |
|------|------|
| `alembic upgrade head` | 升级到最新迁移 |
| `alembic downgrade base` | 回滚到初始状态 |
| `alembic current` | 查看当前版本 |
| `alembic history` | 查看迁移历史 |
| `alembic revision --autogenerate -m "msg"` | 创建新迁移 |

---

## 九、故障排除

### 问题 1：PostgreSQL 连接失败

```
sqlalchemy.exc.OperationalError: connection refused
```

**解决方案：**
```bash
# 检查 Docker 容器是否运行
docker compose ps

# 如果 PostgreSQL 未运行
docker compose up -d postgres

# 等待几秒后重试
sleep 5
curl http://localhost:8000/health
```

### 问题 2：pgvector 扩展未安装

```
ERROR: type "vector" does not exist
```

**解决方案：**
```bash
# 使用 pgvector 镜像（docker-compose.yml 已配置）
docker compose down
docker compose up -d postgres

# 或手动安装
docker compose exec postgres psql -U postgres -d mathpaperforge -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

### 问题 3：Alembic 迁移失败

```
alembic.util.exc.CommandError: Can't locate revision identified by 'xxx'
```

**解决方案：**
```bash
cd backend

# 完全重置
alembic downgrade base
alembic upgrade head
```

### 问题 4：前端启动报错

```
Error: Cannot find module 'xxx'
```

**解决方案：**
```bash
cd frontend

# 清除缓存重新安装
rm -rf node_modules pnpm-lock.yaml
pnpm install
pnpm dev
```

### 问题 5：API Key 无效

```
AuthenticationError: Invalid API Key
```

**解决方案：**
```bash
# 检查 .env 文件中的 API Key 是否正确
# 确保没有多余的空格或引号
cat .env | grep API_KEY

# 测试 API Key
curl https://api.anthropic.com/v1/messages \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01"
```

### 问题 6：PDF 导出失败

```
PDF 导出失败（请确认系统已安装 xelatex）
```

**解决方案：**
```bash
# 检查 xelatex 是否安装
xelatex --version

# 如果未安装：
# Windows: 安装 MiKTeX 或 TeX Live
# macOS: brew install --cask mactex
# Linux: sudo apt install texlive-xetex texlive-lang-chinese
```

### 问题 7：端口被占用

```
ERROR: [Errno 98] Address already in use
```

**解决方案：**
```bash
# 查找占用端口的进程
# Windows:
netstat -ano | findstr :8000
# macOS/Linux:
lsof -i :8000

# 终止进程或更换端口
uvicorn app.main:app --reload --port 8001
```

### 问题 8：Redis 连接失败

```
redis.exceptions.ConnectionError: Connection refused
```

**解决方案：**
```bash
docker compose up -d redis
docker compose exec redis redis-cli ping  # 应返回 PONG
```

---

## 十、生产部署

### 10.1 使用生产 Docker Compose

```bash
# 构建生产镜像
make build

# 启动生产环境
make prod

# 查看日志
docker compose -f docker-compose.prod.yml logs -f

# 停止
make prod-down
```

### 10.2 生产环境配置

生产 `.env` 需要修改：

```env
APP_ENV=production
APP_DEBUG=false
APP_SECRET_KEY=<随机生成的强密钥>
APP_LOG_LEVEL=WARNING
```

### 10.3 生产架构

```
                    ┌─────────────┐
                    │   Nginx:80  │  ← 反向代理 + 静态文件
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
        ┌─────┴─────┐ ┌───┴───┐ ┌──────┴──────┐
        │ Frontend  │ │Backend│ │  WebSocket  │
        │ (static)  │ │ :8000 │ │   :8000     │
        └───────────┘ └───┬───┘ └──────┬──────┘
                          │            │
                    ┌─────┴────────────┴─────┐
                    │     PostgreSQL:5432     │
                    │     Redis:6379          │
                    └────────────────────────┘
```

---

## 附录：项目目录结构速查

```
mathpaperforge/
├── .env.example          # 环境变量模板
├── .env                  # 实际环境变量（需创建）
├── docker-compose.yml    # 开发环境 Docker 配置
├── Makefile              # 快捷命令
├── SETUP_GUIDE.md        # 本文档
│
├── backend/              # Python/FastAPI 后端
│   ├── pyproject.toml    # Python 依赖配置
│   ├── alembic.ini       # 数据库迁移配置
│   ├── alembic/          # 迁移脚本
│   ├── app/              # 应用代码
│   │   ├── main.py       # 入口
│   │   ├── config.py     # 配置
│   │   ├── models/       # 数据库模型
│   │   ├── schemas/      # Pydantic Schema
│   │   ├── api/          # API 路由
│   │   ├── services/     # 业务逻辑
│   │   ├── agents/       # AI Agent
│   │   ├── core/         # 核心模块
│   │   └── middleware/   # 中间件
│   ├── scripts/          # 种子数据脚本
│   └── tests/            # 测试
│
├── frontend/             # React/TypeScript 前端
│   ├── package.json      # Node 依赖配置
│   ├── vite.config.ts    # Vite 配置
│   └── src/
│       ├── api/          # API 调用
│       ├── pages/        # 页面组件
│       ├── components/   # 通用组件
│       ├── stores/       # Zustand 状态
│       └── types/        # TypeScript 类型
│
├── uploads/              # 上传文件存储
└── exports/              # 导出文件存储
```

---

> **快速开始（3 条命令）：**
> ```bash
> docker compose up -d postgres redis   # 启动数据库
> cd backend && alembic upgrade head && python -m scripts.seed_knowledge && python -m scripts.seed_questions && python -m scripts.seed_templates  # 初始化数据
> cd backend && uvicorn app.main:app --reload --port 8000  # 启动后端（新终端启动前端）
> ```
