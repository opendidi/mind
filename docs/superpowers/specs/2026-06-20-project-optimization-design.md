# 项目全面优化设计文档

> 日期：2026-06-20 | 状态：方案已确认，待实施

## 概述

对 mind 项目进行全面的代码质量、架构整理和性能优化，分为 5 层递进执行。

**策略**：分层递进，每层独立可验证，基础设施先行。

---

## 第 1 层：基础设施 — 代码规范 + 自动化

### 1.1 Pre-commit Hooks

新增 `.pre-commit-config.yaml`：

| Hook | 作用 | 范围 |
|------|------|------|
| `black` (v25+) | Python 格式化 | `app/**/*.py` |
| `isort` | import 排序 | `app/**/*.py` |
| `ruff` | Python lint | `app/**/*.py` |
| `prettier` | 前端格式化 | `web/src/**/*.{vue,ts,json,css}` |
| `eslint` | TS/Vue lint | `web/src/**` |
| `trailing-whitespace` | 行尾空格 | 全局 |
| `end-of-file-fixer` | 文件末尾空行 | 全局 |

### 1.2 Ruff 配置

在 `pyproject.toml` 中新增 `[tool.ruff]` 段：

- `line-length = 120`
- `target-version = "py310"`
- `select = ["E", "F", "I", "N", "W", "UP", "B", "C4", "SIM"]`
- `ignore = ["E501"]`（长行交给 black 处理）

### 1.3 Logging 统一

将 18 处 `print()` 替换为 `logging`：

| 文件 | 数量 | 目标级别 |
|------|------|----------|
| `app/package/module/blueprint_mysql.py` | 3 | `logger.error()` |
| `app/package/module/categories_mysql.py` | 1 | `logger.error()` |
| `app/package/module/material_mysql.py` | 1 | `logger.error()` |
| `app/plugin/minio/app/controller.py` | 1 | `logger.error()` |
| `app/util/agent_eval/runner.py` | 8 | `logger.info()` |

### 1.4 首次全量格式化

所有工具配置完毕后，执行一次全量 `black` + `isort` + `prettier`，确保基线一致。

**预估改动**：新增 3 个配置文件，修改 ~22 个文件（18 处 print + 格式化影响）。

---

## 第 2 层：质量安全网 — 测试 + 连接池

### 2.1 后端测试框架 (pytest)

新增 `tests/` 目录：

```
tests/
├── conftest.py              # fixtures: Flask test client, mock DB/Redis/LLM
├── test_agent_core.py       # AgentSession 消息构建、视觉桥接、历史管理
├── test_agent_guard.py      # InputGuard 护栏检测
├── test_agent_tools.py      # 工具函数：canvas、file_search、web_fetch、地理编码
├── test_vision.py           # VisionHandler analyze_base64 / analyze_images
├── test_search_engines.py   # Bing 搜索 HTML 解析、追踪链接解码
├── test_material_mysql.py   # 素材 CRUD、URL segment 提取
├── test_minio.py            # MinIO 对象操作、目录复制
└── test_agent_api.py        # /v1/agent/chat、/v1/agent/tts 端点
```

**测试策略**：
- 核心 Agent 逻辑 → 单元测试（mock LLM，验证消息构建/意图路由/工具调度）
- 外部服务 → mock 返回（`unittest.mock`）
- API 端点 → Flask `test_client` 功能测试
- pytest markers：`@pytest.mark.slow`（集成测试）、`@pytest.mark.unit`（快速）

**pytest 配置**（`pyproject.toml` `[tool.pytest.ini_options]`）：

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
timeout = 30
markers = [
    "unit: fast unit tests",
    "slow: integration tests requiring external services",
]
```

### 2.2 前端测试（最小化）

使用 **vitest + @vue/test-utils**，只加组件冒烟测试：

```
web/src/__tests__/
├── AgentInput.spec.ts       # 渲染、图片粘贴事件、发送 emit
├── ThinkCard.spec.ts        # 展开/折叠逻辑
└── FileCard.spec.ts          # 文件列表渲染、类型图标
```

### 2.3 数据库连接池

`app/package/module/connect.py`：从直接 `pymysql.connect()` 改为 `DBUtils.PooledDB`。

```python
from dbutils.pooled_db import PooledDB
from app.config import db_config

_pool = PooledDB(
    creator=pymysql,
    maxconnections=10,
    mincached=2,
    maxcached=5,
    blocking=True,
    **db_config
)

def connect_db():
    return _pool.connection()
```

所有调用方的 `connect.close()` 不变（PooledDB 自动回收连接）。

`requirements.txt` 新增 `DBUtils>=3.0`。

### 2.4 测试运行脚本

新增 `scripts/run_checks.sh`：

```bash
#!/bin/bash
set -e
echo "=== Ruff lint ===" && ruff check app/
echo "=== Pytest ===" && pytest tests/ -v --tb=short
echo "=== Frontend lint ===" && cd web && pnpm lint
echo "=== Frontend build ===" && cd web && pnpm build
```

**预估改动**：新增 ~12 个测试文件，修改 3 个文件。

---

## 第 3 层：架构整理 — 去重 + 拆分 + 归包

### 3.1 前端组件去重

**问题**：`MapCard.vue` 和 `RouteCard.vue` 各存在两份（`AgentPanel/` + `chat/`），两版本已分化。

**方案**：合并到 `web/src/components/shared/`，差异通过 props 控制：

```
web/src/components/shared/
├── MapCard.vue       # 合并版，保留 chat/ 的弹窗功能
├── RouteCard.vue     # 合并版
```

- `AgentPanel/` 删除 `MapCard.vue`、`RouteCard.vue`，import 指向 `shared/`
- `chat/` 删除 `MapCard.vue`、`RouteCard.vue`，import 指向 `shared/`
- 新增 prop `showDetailModal?: boolean`（AgentPanel 下不显示弹窗）

### 3.2 后端大文件拆分

| 文件 | 当前行数 | 拆分方案 |
|------|---------|----------|
| `agent_tools.py` (1156行) | → | `tools/tool_validate.py` + `tools/tool_canvas.py` + `tools/tool_file.py` + `tools/tool_geo.py` + `tools/text.py` |
| `search/engines.py` (987行) | → | 按搜索引擎拆：`search/bing.py`、`search/providers.py`（保留统一入口） |
| `search/engine_chain.py` (773行) | → | 提取常量和辅助函数到 `search/utils.py` |

### 3.3 前端大文件拆分

| 文件 | 当前行数 | 拆分方案 |
|------|---------|----------|
| `FileManager/index.vue` (1413行) | → | `FileManager/FileList.vue` + `FileManager/FileToolbar.vue` + 提取逻辑到 `useFileManager.ts` |
| `chat/index.vue` (1062行) | → | `ChatHeader.vue` + 提取 `useChatView.ts` composable |

### 3.4 Agent 包整理

27 个 `agent_*.py` 分散在 `app/util/`，按职责归入子包：

```
app/util/agent/
├── __init__.py         # 统一导出，向后兼容别名
├── core.py             # ← agent_core.py
├── engine.py           # ← agent_engine.py
├── guard.py            # ← agent_guard.py
├── memory.py           # ← agent_memory.py + agent_session_memory.py
├── intent.py           # ← agent_intent.py
├── router.py           # ← agent_router.py
├── planner.py          # ← agent_planner.py
├── dispatcher.py       # ← agent_dispatcher.py
├── executor.py         # ← agent_executor.py
├── supervisor.py       # ← agent_supervisor.py
├── tools.py            # ← agent_tools.py（精简为入口）
├── skills.py           # ← agent_skills.py
├── skills/             # ← agent_skills/ 子包（不变）
├── fallback.py         # ← agent_fallback.py
├── reflexion.py        # ← agent_reflexion.py
├── tracer.py           # ← agent_tracer.py
├── observability.py    # ← agent_observability.py
├── circuit.py          # ← agent_circuit.py
├── cache.py            # ← agent_cache.py
├── adaptive.py         # ← agent_adaptive.py
├── pheromone.py        # ← agent_pheromone.py
├── evaluator.py        # ← agent_evaluator.py + agent_plan_eval.py
├── dag.py              # ← agent_dag.py
├── mcp.py              # ← agent_mcp.py
├── helpers.py          # ← agent_helpers.py
├── tts.py              # ← agent_tts.py
├── eval/               # ← agent_eval/（不变）
├── tools/              # 拆分后的工具子模块
│   ├── __init__.py
│   ├── canvas.py
│   ├── file.py
│   ├── geo.py
│   └── text.py
└── agents/             # ← app/util/agents/（不变）
```

**向后兼容**：`app/util/agent/__init__.py` 导出旧名，让 `from app.util.agent_core import AgentSession` 在过渡期仍可用（DeprecationWarning）。

### 3.5 Config 分离

`app/config/__init__.py` 包含 ~80 行环境变量读取和客户端初始化逻辑。

- 配置**值**保留在 `app/config/__init__.py`
- 初始化**逻辑**（`_vision_client` 创建、lazy check 等）移到 `app/config/bootstrap.py`

**预估改动**：~50+ 文件修改/移动。

---

## 第 4 层：性能优化

### 4.1 前端 Tree-Shaking

**当前**：ant-design-vue 全量注册，打包后 ~600KB。

**方案**：使用 `unplugin-vue-components` 自动按需导入。

```ts
// vite.config.ts
import Components from 'unplugin-vue-components/vite'
import { AntDesignVueResolver } from 'unplugin-vue-components/resolvers'

Components({
  resolvers: [AntDesignVueResolver({ importStyle: 'less' })]
})
```

**`web/src/main.ts`** 移除 `app.use(Antd)` 全量注册，改为仅注册 message、notification 等命令式组件。

预估减少首屏体积 **40-50%**。

### 4.2 LLM 调用优化

#### Token 预算追踪
- 扩展 `agent_observability.py`：每次调用记录 `input_tokens`/`output_tokens`
- 会话级累计统计 → Redis（TTL 24h）
- 日志警告：单次调用 > 4000 token

#### 确定性工具调用缓存
- `agent_cache.py`：相同 tool + 相同 args 5 分钟内直接返回缓存
- Redis key: `tool_cache:{tool_name}:{hash(json.dumps(args, sort_keys=True))}`
- 只缓存 file_search、web_fetch、geocode 等确定性工具

#### System Prompt 按需注入
- `BASE_PROMPT` 拆分为核心身份 prompt + 功能章节
- 按意图（intent）动态选择注入哪些章节（如 no-canvas 场景不注入画布指令）

### 4.3 后端性能

| 项 | 方案 | 预期效果 |
|----|------|----------|
| 搜索结果缓存 | Redis TTL 5min，同关键词复用 | 减少 Bing API 调用 |
| MinIO 大文件 | 改用 presigned GET URL（expiry 10min） | 减少后端带宽 |
| Flask 生产模式 | `FLASK_DEBUG=false` 时关闭 reloader | 减少内存占用 |

**预估改动**：修改 ~10 个文件。

---

## 第 5 层：收尾验证

### 5.1 质量门禁

```bash
ruff check app/                 # Python lint — 零错误
pytest tests/ -v                # 全部测试通过
cd web && pnpm lint             # 前端 lint 通过
cd web && pnpm build            # 前端构建成功
docker compose build             # Docker 镜像构建成功
```

### 5.2 文档更新

- `README.md`：新增「开发指南」章节（pre-commit 安装、测试命令、代码规范）
- `CLAUDE.md`（新增）：项目架构概览、开发约定、常用命令速查

### 5.3 提交策略

每层独立 commit，便于 review 和回滚：

```
1. feat(infra): pre-commit + ruff + prettier + logging统一
2. feat(quality): pytest测试框架 + 连接池 + 核心测试用例
3. refactor(arch): 组件去重 + 大文件拆分 + Agent包整理 + config分离
4. perf: ant-design按需加载 + LLM缓存 + token追踪
5. chore: 文档更新 + CLAUDE.md + 最终验证
```

---

## 影响范围总览

| 层 | 新增文件 | 修改文件 | 删除 | 风险 |
|----|---------|---------|------|------|
| 1 | 3 | ~22 | 0 | 极低（纯格式） |
| 2 | ~12 | 3 | 0 | 低（新增无侵入） |
| 3 | 1 (__init__) | ~50 | 4 (重复组件) | 中（导入路径变更） |
| 4 | 0 | ~10 | 0 | 低（增量改动） |
| 5 | 1 (CLAUDE.md) | 1 | 0 | 极低 |
| **合计** | **~17** | **~86** | **4** | |

---

## 不做什么（YAGNI 边界）

- ❌ 不引入 TypeScript strict mode（改动量过大，超出优化范围）
- ❌ 不迁移 Vue 2 → Vue 3（已是 Vue 3）
- ❌ 不替换 ant-design-vue 为其他 UI 库
- ❌ 不引入微服务拆分
- ❌ 不重写 Agent 架构（只做包整理，不改逻辑）
