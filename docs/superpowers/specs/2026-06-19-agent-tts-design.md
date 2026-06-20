# Agent TTS 语音播放 — 设计文档

**日期**: 2026-06-19
**状态**: 设计完成，待评审

---

## 概述

为 AgentPanel 对话面板集成语音播放功能。采用双轨方案：

- **方案 A（前端兜底）**: 复用已有 `useSpeech.ts`（Web Speech API），零成本即时播放
- **方案 B（主力）**: 后端 ChatTTS（CPU 运行）生成高质量中文语音

触发方式：**手动点击**，每条 assistant 消息下方独立喇叭按钮。

---

## 架构

```
用户点击🔊
    │
    ▼
AgentMessageItem.vue
    │  POST /v1/agent/tts {text}
    ▼
Flask agent_api
    │
    ▼
AgentTTS.generate(text)
    ├── 检查缓存 (text MD5)
    ├── 命中 → 直接返回路径
    └── 未命中 → ChatTTS 推理 → 保存 .wav → 返回路径
    │
    ▼
Response: {audio_url: "/static/tts/xxx.wav"}
    │
    ▼
前端 new Audio(url).play()
```

### 不经过 Agent SSE 流

TTS 是独立的请求-响应 API，不解入 Agent 对话流。理由：
1. ChatTTS CPU 推理慢（10-30s），阻塞 SSE 流不合理
2. 用户手动触发，不需要 Agent 自主决定何时朗读
3. 独立端点后续可替换 TTS 引擎，不影响 Agent 核心逻辑

---

## 新建/修改文件清单

| 层 | 文件 | 操作 | 说明 |
|---|------|------|------|
| 后端 | `app/util/agent_tts.py` | 🆕 新建 | ChatTTS 服务封装 |
| 后端 | `app/api/v1/agent.py` | ✏️ 修改 | 新增 `/agent/tts` POST 路由 |
| 后端 | `app/config/__init__.py` | ✏️ 修改 | 添加 TTS 配置项 |
| 后端 | `requirements.txt` | ✏️ 修改 | 添加 ChatTTS 依赖 |
| 前端 | `web/src/api/agent.ts` | ✏️ 修改 | 新增 `requestTTS()` 函数 |
| 前端 | `web/src/composables/useSpeech.ts` | ✏️ 修改 | 扩展 `speakChatTTS()` |
| 前端 | `web/src/components/AgentPanel/AgentMessageItem.vue` | ✏️ 修改 | 添加喇叭按钮 + 音频播放器 |

---

## 后端组件详设

### `app/util/agent_tts.py` — AgentTTS 类

```python
class AgentTTS:
    def __init__(self, cache_dir="./data/tts_cache"):
        # 延迟加载，不在此处初始化 ChatTTS

    def _load_model(self):
        # ChatTTS.Chat().load(compile=False)  CPU 模式

    def generate(self, text: str) -> str:
        # 1. MD5 文本 → 查缓存
        # 2. 缓存命中 → 直接返回文件路径
        # 3. 未命中 → ChatTTS 推理 → 保存 .wav
        # 4. 返回文件路径

    def get_audio_url(self, filepath: str) -> str:
        # 将本地路径转为可访问的 URL
```

**设计要点**:
- 延迟加载：首次调用 `generate()` 才加载模型，Flask 启动不阻塞
- 缓存：按文本 MD5 hash 缓存 .wav 文件
- 线程安全：`threading.Lock` 保护推理过程
- 文本截断：超过 5000 字自动截断

### `app/api/v1/agent.py` — 新增路由

```python
@agent_api.route("/tts", methods=["POST"])
def agent_tts():
    """
    POST JSON: {"text": "要朗读的文本"}
    Response 200: {"audio_url": "/static/tts/abc123.wav"}
    Response 400: {"error": "text is required"}
    Response 503: {"error": "TTS model not loaded yet"}
    Response 500: {"error": "TTS generation failed: ..."}
    """
```

### `app/config/__init__.py` — 配置项

```python
TTS_ENABLED = True
TTS_CACHE_DIR = "./data/tts_cache"
TTS_VOICE_SEED = 42      # 可选：ChatTTS 音色种子
```

---

## 前端组件详设

### `web/src/api/agent.ts` — requestTTS()

```typescript
export async function requestTTS(text: string, signal?: AbortSignal): Promise<string> {
  const resp = await fetch('/v1/agent/tts', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text }),
    signal,
  })
  if (!resp.ok) {
    const err = await resp.json()
    throw new Error(err.error || 'TTS request failed')
  }
  const data = await resp.json()
  return data.audio_url
}
```

### `web/src/composables/useSpeech.ts` — 扩展

在现有 Web Speech API 基础上新增：

```typescript
function speakChatTTS(text: string, signal?: AbortSignal): Promise<HTMLAudioElement>
// 调用 requestTTS() → 创建 Audio(url) → 返回 audio element
// 支持 AbortController 取消
```

### `AgentMessageItem.vue` — 喇叭按钮

**位置**: 消息气泡下方，独立操作行（方案 B）

```
┌─────────────────────────────────┐
│  AI 头像   消息文本内容          │
│                                 │
│  14:33     📋复制  🔊播放       │  ← 操作行
└─────────────────────────────────┘
```

**状态机**:
```
idle ──点击──▶ loading ──成功──▶ playing ──结束/点击──▶ idle
  ▲               │                  │
  │               │ 失败             │ 点击停止
  │               ▼                  │
  └──── 3s 后 ◀── error ◀───────────┘
```

**图标表现**:
| 状态 | 图标 | 样式 |
|------|------|------|
| idle | 🔊 | 灰色，hover 变蓝 |
| loading | ⏳ | 橙色，旋转动画 |
| playing | ⏹ | 蓝色，脉冲动画 |
| error | 🔊 | 红色，tooltip 显示错误 |

---

## 错误处理

### 后端

| 场景 | HTTP 状态 | 响应 |
|------|----------|------|
| 文本为空 | 400 | `{"error": "text is required"}` |
| 模型未就绪 | 503 | `{"error": "TTS model not loaded yet, retry later"}` |
| 推理异常 | 500 | `{"error": "TTS generation failed: <detail>"}` |
| 磁盘满 | 500 | 清理旧缓存后重试一次，仍失败则返回 error |
| 并发推理 | — | `threading.Lock` 排队，不返回错误 |

### 前端

| 场景 | 处理 |
|------|------|
| 网络超时（>30s） | AbortController 取消，显示 "生成超时" |
| HTTP error | 显示后端返回的错误信息，3s 后恢复 idle |
| 音频加载失败 | 显示 "播放失败"，清理 Audio 对象 |
| 快速点击不同消息 | 取消上一个请求，只处理最新的 |
| 页面离开 | 停止正在播放的音频 |

---

## 边界情况

- **空消息**: 不显示喇叭按钮
- **极短消息**（<2 字）: 不显示喇叭按钮
- **超长消息**（>5000 字）: 后端截断，前端播放截断后的音频
- **重复播放**: 后端按文本 MD5 缓存，秒出
- **流式消息进行中**: 不显示喇叭按钮（只有完成的 assistant 消息才有）
- **用户消息**: 不显示喇叭按钮（只朗读 AI 回复）

---

## 依赖

### Python
- `ChatTTS` — TTS 核心库
- `torch` — ChatTTS 依赖（已安装）

### 前端
- 无新增依赖（复用已有 `useSpeech.ts`）

---

## 测试要点

1. 后端：空文本返回 400
2. 后端：正常文本返回 audio_url 且文件可访问
3. 后端：重复请求同一文本命中缓存
4. 前端：喇叭按钮只出现在完成的 assistant 消息
5. 前端：点击 play → loading → playing 状态流转
6. 前端：错误恢复（断网、超时、后端报错）
7. 前端：快速连点不会同时播放多个音频
