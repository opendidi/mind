# mind — 图形可视化编辑器

基于 [meta2d.js](https://github.com/le5le-com/meta2d.js) 开发的 2D 图形可视化编辑器，支持流程图、架构图、思维导图等多种图表类型的创建与编辑。

**当前版本：** 0.0.2 | **在线预览：** [opendidi.github.io/mind](https://opendidi.github.io/mind)

[![AUR](https://img.shields.io/badge/license-Apache%20License%202.0-blue.svg)](https://github.com/opendidi/mind/blob/main/LICENSE)
[![](https://img.shields.io/badge/version-0.0.2-brightgreen.svg)](https://github.com/opendidi/mind)

---

## 功能特性

### 图形编辑
- 🎨 **丰富图元** — 支持矩形、圆形、三角形、菱形、五边形、星形、文本、图片等基础图形
- 🔗 **智能连线** — 直线、曲线、折线、思维导图曲线，支持多方向箭头
- 📐 **自动布局** — 水平/垂直/网格排列，左/右/居中/上/下对齐
- ↩️ **撤销重做** — 完整的操作历史回退
- 🔍 **鹰眼地图** — 全局缩略图导航
- 🔒 **三种模式** — 编辑 / 预览 / 锁定
- 📏 **标尺与网格** — 辅助精确定位

### 图表类型
| 类型 | 说明 |
|------|------|
| 流程图 | 步骤→判断→分支，带箭头连线 |
| 架构图 | 组件/服务拓扑，依赖关系 |
| 思维导图 | 中心主题→分支→细节，radial 布局 |
| 类图 | UML 类结构 |
| 时序图 | 时间线交互 |
| 活动图 | 业务流程 |
| FTA 图 | 故障树分析 |
| 表单图 | UI 表单布局 |

### 文件管理
- 📁 **树形目录** — 文件夹管理，拖拽移动
- 📤 **上传下载** — 支持图片、SVG、文档
- 👁️ **在线预览** — 图片和 SVG 即时预览
- 📋 **素材库** — 可复用的图形模板

### 蓝图系统
- 💾 **保存加载** — 完整画布状态持久化到后端
- 📤 **多格式导出** — PNG（位图）/ SVG（矢量）/ JSON（数据）
- 🔍 **搜索** — 按名称和分类检索

### AI 助手（NEW）
- 🤖 **自然语言操控画布** — 通过对话创建/编辑图形和连线
- 🧠 **智能图表生成** — 根据描述自动生成流程图、架构图、思维导图
- 📋 **蓝图管理** — 搜索、加载、保存、导出蓝图
- 📐 **自动排版** — AI 驱动的图形排列和对齐
- 🔧 **工具调用可视化** — 实时展示 Agent 的工具调用过程

---

## 技术栈

| 层 | 技术 |
|----|------|
| **前端** | Vue 3 + TypeScript + Vite 4 |
| **UI 库** | Ant Design Vue + TDesign Vue Next |
| **图形引擎** | meta2d.js + 8 个 diagram 插件 |
| **状态管理** | Pinia |
| **后端** | Python 3.8+ / Flask 3.0 |
| **数据库** | MySQL (PyMySQL) |
| **对象存储** | MinIO |
| **LLM** | DeepSeek (主) + OpenAI 兼容 fallback |
| **缓存** | Redis（可选，Agent 系统需要） |
| **包管理** | pnpm (monorepo) |

---

## 项目结构

```
mind/
├── app/                              # Python 后端
│   ├── __init__.py                   # Flask app 工厂
│   ├── config/
│   │   ├── __init__.py               # 环境配置（DB / Redis / LLM）
│   │   └── protocol.py               # API 协议常量
│   ├── api/v1/
│   │   ├── __init__.py               # 注册所有蓝图
│   │   ├── agent.py                  # [NEW] Agent SSE / MCP 端点
│   │   ├── blueprint.py              # 蓝图 CRUD API
│   │   ├── material.py               # 素材管理 API
│   │   └── categories.py             # 分类 API
│   ├── package/module/               # MySQL 数据访问层
│   │   ├── connect.py                # 连接管理
│   │   ├── blueprint_mysql.py        # 蓝图 SQL
│   │   ├── material_mysql.py         # 素材 SQL
│   │   └── categories_mysql.py       # 分类 SQL
│   ├── plugin/
│   │   ├── minio/                    # MinIO 对象存储
│   │   └── oss/                      # Aliyun OSS（遗留）
│   └── util/
│       ├── [原有]                    # file.py, json_response.py 等
│       ├── agent_core.py             # [NEW] AgentSession 会话管理
│       ├── agent_engine.py           # [NEW] AgentEngine 执行引擎
│       ├── agent_dag.py              # [NEW] DAGExecutor 并行执行
│       ├── agent_intent.py           # [NEW] 意图分类 + 计划生成
│       ├── agent_tools.py            # [NEW] 16 个业务工具
│       ├── tool_registry.py          # [NEW] 装饰器式工具注册
│       ├── agent_dispatcher.py       # [NEW] 子 Agent 调度
│       ├── agent_reflexion.py        # [NEW] 工具失败自纠正
│       ├── agent_tracer.py           # [NEW] Span 树调用链追踪
│       ├── agent_pheromone.py        # [NEW] 跨节点信息素黑板
│       ├── agent_plan_eval.py        # [NEW] Plan-Feedback 闭环
│       ├── agent_circuit.py          # [NEW] LLM 熔断保护
│       ├── agent_fallback.py         # [NEW] 多级 LLM 故障转移
│       ├── agent_cache.py            # [NEW] 工具结果缓存
│       ├── agent_mcp.py              # [NEW] MCP 协议封装
│       ├── agent_session_memory.py   # [NEW] 跨会话记忆
│       ├── agent_adaptive.py         # [NEW] 自适应重规划（stub）
│       ├── agent_helpers.py          # [NEW] JSON 修复 / Token 估算
│       ├── executor.py               # [NEW] 线程池管理
│       ├── llm_client.py             # [NEW] LLM 客户端（懒加载）
│       ├── redis_utils.py            # [NEW] Redis 连接池
│       ├── agents/                   # [NEW] 子 Agent
│       │   ├── base.py               # AgentBase（ReAct 循环）
│       │   ├── canvas_agent.py       # CanvasAgent
│       │   ├── blueprint_agent.py    # BlueprintAgent
│       │   ├── file_agent.py         # FileAgent
│       │   └── code_agent.py         # CodeAgent
│       └── agent_skills/             # [NEW] 渐进式提示词
│           ├── canvas_skill.py       # 画布编辑知识
│           ├── blueprint_skill.py    # 蓝图管理知识
│           ├── mindmap_skill.py      # 思维导图知识
│           ├── file_skill.py         # 文件管理知识
│           └── code_skill.py         # 代码生成知识
│
├── web/                              # Vue 3 前端
│   ├── src/
│   │   ├── views/
│   │   │   ├── Index.vue             # 主编辑器页面
│   │   │   └── Preview.vue           # 只读预览页
│   │   ├── components/
│   │   │   ├── Meta2D/               # 核心编辑器组件
│   │   │   │   ├── Header/           # 顶部工具栏
│   │   │   │   ├── Editor/           # meta2d 画布
│   │   │   │   ├── Graphics/         # 左侧图形库
│   │   │   │   ├── Props/            # 右侧属性面板
│   │   │   │   ├── FileProps/        # 画布设置
│   │   │   │   ├── PenProps/         # 图形属性
│   │   │   │   ├── Appearance/       # 多选外观
│   │   │   │   ├── Animate/          # 动画帧
│   │   │   │   ├── Event/            # 事件绑定
│   │   │   │   ├── DataValue/        # 数据绑定
│   │   │   │   └── EditContainer/    # Monaco 代码编辑器
│   │   │   ├── AgentPanel/           # [NEW] AI 对话面板
│   │   │   │   ├── index.vue         # 抽屉容器
│   │   │   │   ├── AgentInput.vue    # 消息输入框
│   │   │   │   ├── AgentMessageItem.vue  # 消息渲染
│   │   │   │   ├── AgentThinkCard.vue    # 思考过程卡片
│   │   │   │   ├── AgentToolCard.vue     # 工具调用卡片
│   │   │   │   ├── AgentPlanCard.vue     # DAG 计划卡片
│   │   │   │   └── AgentStreamHandler.ts # SSE 流式处理
│   │   │   ├── blueprint/            # 蓝图弹窗
│   │   │   └── FileManager/          # 文件管理器
│   │   ├── store/modules/            # Pinia 状态
│   │   ├── api/                      # API 客户端
│   │   ├── router/                   # 路由配置
│   │   └── utils/                    # 工具函数
│   ├── .env                          # 前端环境变量
│   ├── .env.development              # 开发环境
│   └── vite.config.ts                # Vite 构建配置
│
├── docs/                             # GitHub Pages 部署
├── static/                           # 静态资源
├── starter.py                        # 后端启动入口
├── requirements.txt                  # Python 依赖
├── .env.example                      # [NEW] 环境配置模板
└── package.json                      # 根 monorepo 脚本
```

---

## 快速开始

### 环境要求

| 依赖 | 版本 |
|------|------|
| Python | ≥ 3.8.10 |
| Node.js | ≥ 14.18 / 16+ |
| pnpm | 最新版（必须使用 pnpm） |
| MySQL | 5.7+ |
| Redis | 可选（Agent 系统推荐安装） |

### 1. 克隆项目

```bash
git clone https://github.com/opendidi/mind.git
cd mind
```

### 2. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env` 文件，填入实际配置：

```env
# 数据库（必填）
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=your_password
DB_PORT=3306
DB_NAME=mind

# Redis（Agent 系统需要，不可用时自动降级为内存模式）
REDIS_HOST=127.0.0.1
REDIS_PORT=6379
REDIS_PASSWORD=

# LLM API Key（使用 AI 助手功能必须配置）
DEEPSEEK_API_KEY=sk-your-deepseek-api-key
DEEPSEEK_BASE_URL=https://api.deepseek.com

# 可选：Fallback LLM（主 LLM 故障时自动切换）
# FALLBACK1_API_KEY=sk-your-openai-key
# FALLBACK1_BASE_URL=https://api.openai.com/v1
# FALLBACK1_MODEL=gpt-4o-mini
```

### 3. 初始化数据库

确保 MySQL 已运行，创建 `mind` 数据库：

```sql
CREATE DATABASE IF NOT EXISTS mind DEFAULT CHARSET utf8mb4;
```

项目启动时会自动建表。

### 4. 安装依赖

**Python 后端：**

```bash
pip install -r requirements.txt
```

**前端：**

```bash
pnpm install
```

### 5. 启动服务

**启动后端（端口 5001）：**

```bash
python starter.py
```

**启动前端开发服务器（端口 3100）：**

```bash
pnpm dev:web
```

打开浏览器访问 `http://localhost:3100` 即可使用。

> 前端开发环境通过 Vite proxy 将 API 请求转发到 `http://127.0.0.1:5001/v1/`。

### 6. 使用 AI 助手

1. 确保 `.env` 中配置了 `DEEPSEEK_API_KEY`
2. 打开编辑器，点击顶部工具栏右侧的 🤖 **AI 助手** 按钮
3. 在弹出的对话框中输入需求，例如：
   - "帮我画一个用户登录流程图"
   - "把这些图形垂直排列，间距 50px"
   - "搜索名字包含'架构'的蓝图"
   - "生成一个微服务架构的思维导图"

---

## API 接口

### 蓝图管理

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/v1/blueprint/lists` | 分页列表 |
| `GET` | `/v1/blueprint/find?id=` | 按 ID 查询 |
| `POST` | `/v1/blueprint/add` | 创建蓝图 |
| `POST` | `/v1/blueprint/modify` | 修改蓝图 |
| `POST` | `/v1/blueprint/delete` | 删除蓝图 |

### 素材管理

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/v1/material/lists` | 分页列表 |
| `GET` | `/v1/material/folder` | 文件夹树 |
| `GET` | `/v1/material/preview` | 预览文件 |
| `POST` | `/v1/material/upload` | 上传文件 |
| `POST` | `/v1/material/create_dir` | 创建文件夹 |
| `POST` | `/v1/material/delete` | 删除 |
| `POST` | `/v1/material/modify` | 重命名 |
| `POST` | `/v1/material/copy` | 复制 |
| `POST` | `/v1/material/scissors` | 移动 |

### 分类

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/v1/categories/lists` | 分类列表 |

### AI Agent（NEW）

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/v1/agent/chat` | SSE 流式对话 |
| `POST` | `/v1/agent/mcp` | MCP JSON-RPC 工具调用 |

**Agent Chat 请求格式：**

```json
{
  "message": "帮我画一个登录流程图",
  "user_id": "user_001",
  "canvas_context": {
    "pens": [{"id": "p1", "type": "rectangle", "x": 100, "y": 50, "text": "开始"}],
    "lines": []
  }
}
```

**SSE 事件类型：**

| 事件 | 说明 |
|------|------|
| `token` | 逐字输出 |
| `thinking` | 思考过程 |
| `tool_call` | 工具调用开始 |
| `tool_result` | 工具调用结果 |
| `plan` | DAG 执行计划 |
| `step_start/end/fail` | 计划步骤状态 |
| `message` | 完整回复 |
| `trace` | 调用链追踪 ID |
| `error` | 错误信息 |
| `done` | 对话完成 |

---

## Agent 架构

Agent 系统参考 pypano 的 V3 Agent 架构，采用 **基础层完整复刻 + 业务层重新设计** 策略。

### 架构层次

```
用户输入 → AgentSession → Intent分类 → Plan生成
                                    ↓
            SSE流 ← AgentEngine ← DAGExecutor（并行）
                        ↓              ↓
                  Simple ReAct     子Agent调度
                                    ↓
                              ToolRegistry（17个工具）
```

### 请求流程

1. 前端发送 POST `/v1/agent/chat`，后端立即返回 `text/event-stream`
2. 后台线程执行 `AgentSession.chat_v3()`
3. 恢复跨会话记忆 → Plan-Feedback 闭环注入 → 统一 LLM 调用（意图 + 域 + 计划）
4. `AgentEngine` 路由：simple 模式（单轮 ReAct）或 dag 模式（多节点并行）
5. DAG 模式下：拓扑排序 → 并行执行节点 → 反思纠正 → 信息素沉积 → 自适应重规划
6. 所有事件（工具调用/结果/思考/计划）通过 SSE 流推送前端实时展示

### 工具集（17 个）

| 域 | 工具 | 说明 |
|----|------|------|
| **Canvas** | `canvas_add_pen` | 创建图形 |
| | `canvas_update_pen` | 修改图形 |
| | `canvas_delete_pen` | 删除图形 |
| | `canvas_add_line` | 创建连线 |
| | `canvas_get_state` | 获取画布状态 |
| | `canvas_clear` | 清空画布 |
| | `canvas_undo/redo` | 撤销/重做 |
| **Blueprint** | `blueprint_list` | 蓝图列表 |
| | `blueprint_load` | 加载蓝图 |
| | `blueprint_save` | 保存蓝图 |
| | `blueprint_search` | 搜索蓝图 |
| | `blueprint_export` | 导出文件 |
| **Layout** | `layout_auto_arrange` | 自动排列 |
| | `layout_align` | 对齐图形 |
| **辅助** | `file_search` | 搜索素材 |
| | `code_generate` | 生成代码 |

### 子 Agent

| Agent | 工具 | 职责 |
|-------|------|------|
| `canvas_agent` | canvas_* + layout_* | 画布图形创建、编辑、布局 |
| `blueprint_agent` | blueprint_* | 蓝图搜索、加载、保存、导出 |
| `file_agent` | file_search | 文件/素材检索管理 |
| `code_agent` | code_generate | JavaScript/JSON 代码生成 |

### 高级特性

| 特性 | 说明 |
|------|------|
| **DAG 并行执行** | 无依赖步骤同时执行，拓扑排序调度 |
| **AgentReflexion** | 工具失败自动分析原因，retry/skip/escalate 三级策略 |
| **Pheromone 黑板** | 跨节点共享已发现的信息，避免重复查询 |
| **Plan-Feedback 闭环** | 执行后评分 → 历史教训 → 下次规划注入 |
| **Circuit Breaker** | LLM 连续失败 5 次自动熔断，30 秒冷却 |
| **Fallback LLM** | 主 LLM 故障时透明切换到备用 |
| **Context Compaction** | LLM 驱动的对话历史压缩，防止 token 超限 |
| **Streaming SSE** | 逐 Token + 工具调用实时流式输出 |
| **Tracing** | OpenTelemetry 风格的 Span 树调用链追踪 |
| **Redis 降级** | Redis 不可用时自动切换为内存模式 |

---

## 构建部署

### 前端构建

```bash
pnpm build:web
```

构建产物输出到 `docs/` 目录（用于 GitHub Pages 部署）。

修改输出目录：编辑 `web/build/constant.ts`：

```js
export const OUTPUT_DIR = '../docs';
```

### 后端部署

```bash
# 生产环境建议使用 gunicorn
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5001 'app:create_app()'
```

---

## 相关资源

- [meta2d.js 开源仓库](https://github.com/le5le-com/meta2d.js)
- [meta2d.js 文档](https://doc.le5le.com/document/119359590)
- [项目在线预览](https://opendidi.github.io/mind)

## License

[Apache License 2.0](LICENSE)
