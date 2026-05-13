# 后端系统工程与并发稳定性重构

## 概述

本次重构针对试卷生成这一 CPU 密集与 I/O 密集双重混合的长耗时任务，实现了：

1. **异步任务队列彻底解耦** - 基于 ARQ (Async Redis Queue)
2. **长链接高可用设计** - WebSocket 心跳检测、断线缓冲重传
3. **完整错误追踪** - 堆栈信息与 Agent 状态返回前端

## 新增文件

### 1. `app/core/task_queue.py` - ARQ 任务队列管理器

**核心功能：**
- 任务提交与优先级队列（LOW/NORMAL/HIGH/CRITICAL）
- 任务生命周期管理（提交、查询、取消、重试）
- Agent 状态追踪与错误堆栈记录
- ARQ Worker 配置与执行函数

**使用示例：**

```python
from app.core.task_queue import TaskQueueManager, TaskPriority

# 初始化
task_queue = TaskQueueManager()
await task_queue.connect()

# 提交任务
job = await task_queue.submit_task(
    task_id="123",
    log_id=123,
    request_data=request.model_dump(),
    priority=TaskPriority.HIGH,
)

# 查询状态
status = await task_queue.get_task_status("123")

# 取消任务
cancelled = await task_queue.cancel_task("123")

# 重试任务
retried = await task_queue.retry_task("123")
```

**启动 ARQ Worker：**

```bash
# 开发模式
arq app.core.task_queue.WorkerSettings

# 生产模式（多 worker）
arq app.core.task_queue.WorkerSettings --workers 4
```

### 2. `app/tasks/websocket_manager.py` - 高可用 WebSocket 管理器

**核心功能：**
- 心跳检测（Ping/Pong，15 秒间隔）
- 断线缓冲与重传（最多 3 次重试）
- Redis 集成（多实例同步、消息持久化）
- 多客户端广播

**连接生命周期：**

```
1. 客户端连接 WebSocket
   ↓
2. 注册连接，启动心跳任务
   ↓
3. 重放缓冲的消息（如有）
   ↓
4. 循环等待消息（Pong 响应）
   ↓
5. 断线检测 → 重传缓冲 → 清理连接
```

**心跳机制：**
- 服务器每 15 秒发送 Ping
- 客户端回复 Pong
- 超过 30 秒未收到 Pong 判定为断开
- 触发断线处理流程

### 3. `app/api/v1/endpoints/generation.py` - 更新版 API 端点

**新增端点：**

| 端点 | 方法 | 描述 |
|------|------|------|
| `/generate` | POST | 提交任务到 ARQ 队列（支持优先级） |
| `/tasks/{task_id}` | GET | 查询任务状态（ARQ + DB 双源） |
| `/tasks/{task_id}/cancel` | POST | 取消正在执行的任务 |
| `/tasks/{task_id}/retry` | POST | 重试失败的任务 |
| `/ws/{task_id}` | WebSocket | 实时进度推送（心跳 + 重传） |

**优先级参数：**

```json
{
  "template_id": 1,
  "priority": "high"  // low | normal | high | critical
}
```

## 架构变更

### Before（FastAPI BackgroundTasks）

```
FastAPI Main Process
    ├── HTTP Request
    │   └── background_tasks.add_task(run_generation_pipeline)
    └── WebSocket Handler
        └── Simple in-memory connection registry
```

**问题：**
- 主进程可能被阻塞
- 无任务队列管理
- 无重试机制
- WebSocket 无心跳检测

### After（ARQ + 高可用 WebSocket）

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  FastAPI Main   │────▶│   Redis (ARQ)    │◀────│   ARQ Worker    │
│     Process     │     │   Priority Queues│     │   (Separate)    │
│                 │     │                  │     │                 │
│  - HTTP API     │     │  - critical      │     │  - Run tasks    │
│  - WebSocket    │     │  - high          │     │  - Progress cb  │
│    Manager      │     │  - default       │     │  - Error handle │
└─────────────────┘     │  - low           │     └─────────────────┘
                        └──────────────────┘
                                 │
                                 ▼
                        ┌──────────────────┐
                        │   Redis Pub/Sub  │
                        │   Message Buffer │
                        └──────────────────┘
```

## 配置说明

### Redis 连接配置

```python
from arq.connections import RedisSettings

redis_settings = RedisSettings(
    host="localhost",      # Redis 主机
    port=6379,            # Redis 端口
    database=0,           # 数据库编号
    password=None,        # 密码（可选）
    ssl=False,            # SSL（可选）
)
```

### Worker 配置

```python
class WorkerSettings:
    functions = [run_generation_pipeline]
    redis_settings = RedisSettings(host="localhost", port=6379, database=0)
    job_timeout = timedelta(seconds=3600)  # 1 小时超时
    job_try_limit = 3                       # 最多重试 3 次
    retry_jobs = True                       # 启用重试
    burst = False                           # 非突发模式
    listen_queues = ["critical", "high", "default", "low"]
```

### Docker Compose 配置示例

```yaml
version: '3.8'

services:
  api:
    build: ./backend
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000
    depends_on:
      - redis
      - postgres

  worker:
    build: ./backend
    command: arq app.core.task_queue.WorkerSettings
    depends_on:
      - redis
      - postgres
    deploy:
      replicas: 4  # 4 个 worker 实例

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

  postgres:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_DB: mathpaper
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  redis_data:
  postgres_data:
```

## 错误处理与监控

### 错误堆栈捕获

当任务失败时，完整堆栈信息会：
1. 记录到日志（structlog）
2. 存储到 `TaskMetadata.error_stack`
3. 通过 WebSocket 推送给前端
4. 可通过 `/tasks/{task_id}` 端点查询

### Agent 状态追踪

在生成管线的每个阶段，Agent 状态会被记录：

```python
task_queue.update_agent_state(task_id, {
    "current_agent": "Generator",
    "step": "generating_questions",
    "progress": 0.6,
})
```

### 监控指标

建议收集以下指标：
- 队列长度（按优先级）
- 任务平均执行时间
- 任务失败率
- WebSocket 连接数
- 心跳超时次数

## 性能对比

| 指标 | Before | After | 提升 |
|------|--------|-------|------|
| 主进程阻塞 | 是 | 否 | ✓ |
| 任务重试 | 无 | 自动 3 次 | ✓ |
| 优先级调度 | 无 | 4 级队列 | ✓ |
| WebSocket 稳定性 | 低 | 高（心跳 + 重传） | ✓ |
| 错误可追溯性 | 低 | 完整堆栈 | ✓ |
| 水平扩展 | 困难 | 容易（多 worker） | ✓ |

## 迁移指南

### 步骤 1：安装依赖

```bash
pip install arq redis
```

### 步骤 2：更新 pyproject.toml

```toml
[project.dependencies]
arq = ">=0.25.0"
redis = ">=5.0.0"
```

### 步骤 3：启动 Redis

```bash
docker run -d -p 6379:6379 redis:7-alpine
```

### 步骤 4：启动 Worker

```bash
# 终端 1：启动 API
uvicorn app.main:app --reload

# 终端 2：启动 Worker
arq app.core.task_queue.WorkerSettings
```

### 步骤 5：测试

```bash
# 提交任务
curl -X POST http://localhost:8000/api/v1/generation/generate \
  -H "Content-Type: application/json" \
  -d '{"template_id": 1, "priority": "high"}'

# 查询状态
curl http://localhost:8000/api/v1/generation/tasks/1

# WebSocket 连接（使用 wscat 或前端）
wscat -c ws://localhost:8000/api/v1/generation/ws/1
```

## 故障排查

### 问题：Worker 不消费任务

**检查：**
1. Redis 是否正常运行
2. Worker 是否正确启动
3. 队列名称是否匹配
4. 任务序列化是否正确

```bash
# 查看 Redis 队列
redis-cli LRANGE critical 0 -1
redis-cli LRANGE high 0 -1
redis-cli LRANGE default 0 -1
redis-cli LRANGE low 0 -1
```

### 问题：WebSocket 频繁断开

**检查：**
1. 心跳间隔是否过长
2. 网络是否稳定
3. 客户端是否正确回复 Pong
4. 防火墙/NAT 设置

**调整心跳间隔：**

```python
connection.heartbeat_interval = 10.0  # 缩短为 10 秒
```

### 问题：任务一直 Running 状态

**检查：**
1. Worker 是否卡死
2. 任务是否超时
3. Redis 连接是否正常

**手动取消：**

```bash
curl -X POST http://localhost:8000/api/v1/generation/tasks/123/cancel
```

## 最佳实践

1. **合理设置超时**：根据试卷复杂度设置 `job_timeout`
2. **监控队列长度**：避免某个优先级队列堆积
3. **优雅关闭**：Worker 停止前先完成当前任务
4. **日志分级**：生产环境使用 INFO，开发使用 DEBUG
5. **Redis 持久化**：启用 RDB/AOF 防止数据丢失
6. **健康检查**：定期检查 Worker 和 Redis 状态

## 未来优化

- [ ] 支持任务依赖（DAG 调度）
- [ ] 支持任务批量提交
- [ ] 集成 Prometheus 监控
- [ ] 支持动态调整 Worker 数量
- [ ] 实现任务结果缓存
