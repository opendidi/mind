# Mind Project — 开发指南

## 项目概览

mind 是一个 AI Agent 系统，支持多模态视觉理解、文件管理、画布操作、蓝图编辑、地图/路线规划等功能。

### 技术栈

| 层级 | 技术 |
|------|------|
| **后端框架** | Flask 3.0 + eventlet |
| **Agent 系统** | 六层架构（Guard → Intent → Planner → Executor → Supervisor → Memory） |
| **LLM** | DeepSeek API（主）+ 多级 Fallback |
| **数据库** | MySQL 8.0 (PyMySQL + DBUtils 连接池) |
| **缓存** | Redis 7（会话、搜索缓存、Agent 记忆） |
| **对象存储** | MinIO（文件/素材/全景图） |
| **前端** | Vue 3 + Vite 4 + TypeScript |
| **UI** | Ant Design Vue 3.2 + TDesign（图标/ColorPicker） |
| **可视化** | Meta2D（画布编辑器）、ECharts（图表）、AMap（地图） |
| **部署** | Docker Compose |

### 项目架构

```
app/
├── api/v1/          # REST API (agent, auth, chat, material, blueprint, categories)
├── config/          # 环境变量 + 配置常量
├── package/module/  # 数据库模块 (MySQL CRUD)
├── plugin/          # 扩展 (auth, minio, oss)
└── util/
    ├── agent/       # Agent 核心包 (27 个子模块)
    │   ├── core.py      # AgentSession — 消息构建、视觉桥接、会话管理
    │   ├── engine.py    # AgentEngine — 统一执行入口
    │   ├── guard.py     # InputGuard / ToolGuard / OutputGuard
    │   ├── intent.py    # 意图分类 + 统一意图规划
    │   ├── router.py    # 意图 → Skill 路由
    │   ├── planner.py   # 任务规划器
    │   ├── executor.py  # 工具执行器
    │   ├── tools.py     # 工具函数集 (canvas, file, geo, text, web)
    │   ├── skills/      # 按域技能模块 (canvas, blueprint, file, mindmap, code)
    │   ├── memory.py    # 长期记忆管理
    │   ├── dag.py       # DAG 执行引擎
    │   ├── cache.py     # 工具结果缓存 + 确定性缓存
    │   ├── observability.py  # 结构化追踪 + Token 预算
    │   └── eval/        # Agent 评估框架
    ├── search/      # 搜索引擎 (Bing + fallback)
    ├── vision.py    # 视觉分析 (DeepSeek Vision)
    └── llm_client.py   # LLM 通用客户端
web/
├── src/
│   ├── components/
│   │   ├── AgentPanel/  # Agent 对话面板
│   │   ├── chat/        # 聊天组件
│   │   └── shared/      # 共享组件 (MapCard, RouteCard)
│   ├── composables/     # Vue Composables (useAgentChat, useSpeech, useConversations)
│   ├── views/           # 页面 (chat, Preview, user)
│   └── utils/           # 工具 (canvasBridge, graphicGroups)
```

## 开发环境

### 安装

```bash
# 前端
pnpm install

# 后端（Docker）
docker compose up -d --build
```

### 代码规范

项目已配置 pre-commit hooks：

```bash
# 安装 hooks（首次）
pip install pre-commit && pre-commit install

# 手动运行
python -m ruff check app/      # Python Lint
python -m ruff format app/     # Python Format
cd web && pnpm format          # 前端 Format
```

### 测试

```bash
# 后端测试
pytest tests/ -v --tb=short

# 前端测试
cd web && npx vitest run

# 全量质量门禁
bash scripts/run_checks.sh
```

### 配置规范

- `.env.example` — 所有可配置项的模板
- `.env` — 本地配置（gitignore）
- `app/config/__init__.py` — 只放配置值定义，不放初始化逻辑

## 关键约定

### Commit 规范

遵循 Conventional Commits：
- `feat:` — 新功能
- `fix:` — Bug 修复
- `refactor:` — 重构
- `perf:` — 性能优化
- `docs:` — 文档
- `chore:` — 杂项

### Agent 包导入

```python
# ✅ 推荐：新导入
from app.util.agent.core import AgentSession
from app.util.agent.guard import InputGuard

# ⚠️ 已弃用：旧路径（仍可用但会触发 DeprecationWarning）
from app.util.agent_core import AgentSession
```

### Logging

- 使用 `logging` 模块，不要用 `print()`
- 错误级别：业务异常用 `logging.warning()`，系统错误用 `logging.error()`
- 格式：`f"模块名 操作 错误：{e}"`

### 错误处理

- 统一中英文错误消息（用户可读 → 中文，内部日志 → 英文）
- 所有 `except:` 必须记录日志
- 禁止吞异常（bare except without logging）
