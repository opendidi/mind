# -*- coding: UTF-8 -*-
"""
Agent 核心 — V3 统一入口: DAG + Multi-Agent + Tracing + Skills

用法:
  session = AgentSession(user_id)
  for event in session.chat_v3("帮我画一个登录流程图"):
      yield sse_format(event)

架构:
  AgentSession  ── 管理对话历史 + 上下文注入 + Skills 动态加载 + SSE 事件输出
  AgentEngine   ── V3 统一执行引擎（agent_engine.py）
  ToolRegistry  ── 装饰器式工具注册（agent_tools.py）
"""

import json
import logging
import time
from datetime import datetime

from app.config import AGENT_DEFAULT_MODEL
from app.util.agent.engine import AgentEngine
from app.util.agent.intent import classify_domain, unified_intent_and_plan
from app.util.agent.skills import get_skills_for_intent
from app.util.llm_client import get_llm_client
from app.util.agent.helpers import estimate_tokens_from_str as _estimate_tokens

MAX_HISTORY_TOKENS = 8000
MAX_HISTORY_COMPACT = 4000


# ── Base Prompt ───────────────────────────────────────────────────────────

BASE_PROMPT = """你是"小M"，一个智能助手，专注于帮助用户创建和编辑 2D 图表、蓝图和思维导图，同时也能自然地进行日常对话和知识问答。

## [!] 第一步：判断意图（最高优先级）

每次回复前先判断用户意图，决定是否需要调用工具：

| 意图类型 | 示例 | 处理方式 |
|---------|------|---------|
| **实时信息查询** | "有什么新闻""今天天气怎么样""最新XX是什么" | 用 web_search 搜索后总结回答。必须提供 keyword 参数（从用户问题中提取关键词）。例如问"有什么新闻"→ `web_search(keyword="今日新闻", search_type="news", timelimit="w")`。 |
| **闲聊/知识问答** | "解释机器学习""推荐一本书""Python 怎么学" | **直接用自身知识回复**，不调用工具。这类常识性问题不需要搜索。 |
| **图形查看** | "画布上有什么""当前有哪些节点" | 用 canvas(action='get_state') 查看后回复 |
| **图形编辑** | "画一个流程图""删除那个矩形" | 必须调用对应工具完成实际操作 |

[!] 判断标准：时效性问题（新闻/天气/最新）→ 搜索；常识知识 → 直接回答；图形相关 → 对应工具。

## [!!] 核心铁律（图形操作时）

1. **写操作必须调用工具！** 创建、修改、删除图形等操作绝对不能仅用文字回复。不调用工具就说"已完成"是欺骗用户，绝对禁止。
2. **只看工具结果！** 只有当工具返回 `success: true` 时才报告成功。失败时必须如实告知原因。
3. **没有捷径！** 不存在"告知系统""通知系统"等绕过工具的魔法方式。你唯一执行操作的方式就是调用工具函数。

## 行为准则

- **先判断再行动** — 区分对话和操作，对话不需要工具
- **先看再动** — 如需确认画布现状，用 canvas(action='get_state') 查看
- **先规划后执行** — 复杂任务用 `[思考]` 简述步骤（1~2句），再逐步执行
- **确认删除** — 删除图形或清空画布前向用户确认并说明后果
- **不要加戏** — 只执行用户明确要求的操作，不自行扩展
- **失败止损** — 同一操作连续失败 2 次即停止，向用户说明原因
- **主动建议** — 完成操作后可附带一条简短建议
- **位置可视化** — 涉及地点/坐标时主动附上 ```map 代码块展示位置
- **路线规划** — 用户询问两地之间怎么走时，先用 geocode 查询起终点坐标，再用 ```route 代码块输出路线
- **知识问答** — 用户问知识性问题时直接回答，不要尝试画图或调用工具

## 回复格式

- 用中文回复，简洁专业，语气友好
- 操作成功 → 简明告知结果
- 操作失败 → 说明原因 + 替代方案

## 地图标记格式 (```map)

输出 JSON，center 为中心经纬度，markers 为标记数组：
```map
{
  "title": "位置标注",
  "center": [lng, lat],
  "zoom": 14,
  "markers": [
    {
      "lat": 22.81,
      "lng": 113.29,
      "title": "地点名称",
      "desc": "描述信息（可选）"
    }
  ]
}
```

## 路线规划格式 (```route)

输出 JSON，mode 为路线模式，from/to 为起终点坐标与名称：
```route
{
  "mode": "driving",
  "from": { "lng": 113.29, "lat": 22.81, "name": "广州塔" },
  "to": { "lng": 113.95, "lat": 22.53, "name": "深圳湾公园" }
}
```
mode 可选值：driving(驾车) / walking(步行) / riding(骑行) / transit(公交)

## 视觉能力（图片理解）

你可以理解用户上传的图片内容。当用户贴图时，系统会自动通过视觉模型分析图片并生成文字描述，以 `[系统提示] 用户在此消息中附带了 N 张图片...` 的格式注入到用户消息中。
- 收到图片描述后，充分利用其中的信息回答用户问题
- 当用户贴了架构图/流程图/截图/照片时，先复述你理解到的关键内容，再据此执行操作
- 如果用户要求"照着图画"，根据描述中的结构/元素/关系调用 canvas 工具在画布上重建
- 如果图片描述中包含了可操作的信息（如节点名、连接关系、布局等），主动建议用户是否需要在画布上绘制

## 支持的图形类型

- rectangle（矩形）、circle（圆形）、triangle（三角形）、diamond（菱形）
- pentagon（五边形）、star（星形）、text（文本）、image（图片）
- 连线类型：straight（直线）、curve（曲线）、polyline（折线）、mind（思维导图线）
- 连线箭头：start/end/both/none

## 思维导图格式 (```mindmap)

输出标准 Markdown 无序列表，每行一项，缩进表示层级：
```mindmap
- 根主题
  - 子主题1
    - 细节A
  - 子主题2
```

## 文件列表格式 (```files)

当使用 file_search 搜索到文件后，如有图片文件，用 ```files 代码块展示文件列表：
```files
[
  {"name": "文件名.jpg", "url": "文件完整URL", "type": "image", "extension": "jpg", "size": 12345},
  {"name": "文档.pdf", "url": "URL", "type": "document", "extension": "pdf", "size": 67890}
]
```

## 常见图表类型

- **流程图**：矩形=步骤，菱形=判断，圆形=开始/结束，带箭头连线表示流向
- **架构图**：矩形=组件/服务，连线=依赖/数据流
- **思维导图**：中心主题→分支→细节，使用 mind 曲线连接
"""

# ── Compaction Prompt ────────────────────────────────────────────────────

COMPACT_PROMPT = """将以下对话历史压缩为关键要点摘要（中文，不超过 500 字）。
保留：用户做了什么操作、工具调用结果、重要数据和当前状态。
丢弃：闲聊、重复内容、纯确认性回复。

对话历史:
"""


def _msg_tokens(msg: dict) -> int:
    tokens = _estimate_tokens(msg.get("content", "") or "")
    for tc in msg.get("tool_calls", []) or []:
        fn = tc.get("function", {})
        tokens += _estimate_tokens((fn.get("name") or "") + (fn.get("arguments") or ""))
    return tokens


class AgentSession:
    """单次 Agent 会话，管理对话历史与上下文。"""

    def __init__(self, user_id: str):
        self.user_id = user_id
        self.history: list = []
        self.created_at = time.time()
        self._compact_summary: str = ""

    def _compact_history(self, llm_client, model: str = AGENT_DEFAULT_MODEL):
        """LLM-driven context compaction."""
        if not self.history:
            return

        total = sum(_msg_tokens(m) for m in self.history)
        if total <= MAX_HISTORY_COMPACT:
            return

        cumulative = 0
        split_at = 0
        for i, m in enumerate(self.history):
            cumulative += _msg_tokens(m)
            if cumulative >= total * 0.5:
                split_at = i + 1
                break

        if split_at < 2:
            return

        old_msgs = self.history[:split_at]
        recent_msgs = self.history[split_at:]

        compact_lines = []
        for m in old_msgs:
            role = m.get("role", "")
            content = (m.get("content") or "")[:300]
            if role == "user":
                compact_lines.append(f"用户: {content}")
            elif role == "assistant":
                compact_lines.append(f"助手: {content}")
            elif role == "tool":
                compact_lines.append(f"工具结果: {content[:200]}")

        compact_text = "\n".join(compact_lines)
        if not compact_text.strip():
            return

        try:
            resp = llm_client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": COMPACT_PROMPT + compact_text[:3000]}],
                temperature=0.1, max_tokens=400, timeout=15,
            )
            summary = resp.choices[0].message.content or ""
            if summary.strip():
                prev = self._compact_summary
                if prev:
                    merged = f"{prev}\n---\n{summary.strip()}"
                    if len(merged) > 2000:
                        merged = f"...(较早对话已省略)\n{summary.strip()}"
                        if len(merged) > 2000:
                            merged = merged[-2000:]
                    self._compact_summary = merged
                else:
                    self._compact_summary = summary.strip()
                self.history = recent_msgs
                logging.info("Context compacted: %d msgs → summary (%d chars), kept %d recent",
                             len(old_msgs), len(self._compact_summary), len(recent_msgs))
        except Exception:
            logging.warning("Compaction LLM call failed, falling back to truncation", exc_info=True)
            self.history = recent_msgs

    def _trim_history(self):
        """Fallback truncation when compaction isn't possible.

        Only truncates when the total token estimate exceeds the budget.
        The `trimmed_at` sentinel pattern avoids the fencepost bug where
        keep_from stayed at len(self.history) and wiped everything.
        """
        if not self.history:
            return
        total = 0
        trimmed_at = None  # sentinel: only truncate if actually over budget
        for i in range(len(self.history) - 1, -1, -1):
            tokens = _msg_tokens(self.history[i])
            if total + tokens > MAX_HISTORY_TOKENS:
                trimmed_at = i + 1
                break
            total += tokens
        if trimmed_at is None:
            return  # under budget — nothing to do
        if trimmed_at >= len(self.history):
            return  # edge: trim point at very end — nothing to drop
        # Avoid starting on an assistant-only message (loses context)
        if self.history[trimmed_at].get("role") == "assistant":
            trimmed_at = min(trimmed_at + 1, len(self.history) - 1)
        logging.info("Agent 历史截断：%d → %d 条", len(self.history), len(self.history) - trimmed_at)
        self.history = self.history[trimmed_at:]

    def _build_system_prompt(self, user_message: str, canvas_context: dict = None,
                             memory_prompt: str = "", unified_result: dict = None,
                             session_memory: str = "", skill_context: dict = None) -> str:
        """Build a single merged system prompt."""
        now = datetime.now()
        time_hint = (
            f"现在是 {now.year} 年 {now.month} 月 {now.day} 日，"
            f"星期{'一二三四五六日'[now.weekday()]}，北京时间 {now.strftime('%H:%M')}。"
        )

        sections = [BASE_PROMPT, time_hint]

        # Skills — dynamic per intent
        domains = (unified_result or {}).get("domains") or classify_domain(user_message)
        skills_text = get_skills_for_intent(domains, context=skill_context)
        if skills_text:
            sections.append(skills_text)

        # Session memory
        if session_memory:
            sections.append(session_memory)

        # Compaction summary
        if self._compact_summary:
            sections.append(f"## 历史摘要\n{self._compact_summary}")

        # Canvas context (current editor state from frontend)
        if canvas_context:
            sections.append(f"## 当前画布状态\n{json.dumps(canvas_context, ensure_ascii=False, indent=2)}")

        # User memory
        if memory_prompt:
            sections.append(memory_prompt)

        # Write guard
        has_write = (unified_result or {}).get("has_write", False)
        if has_write:
            sections.append("[!] 用户要求执行写操作（创建/修改/删除）。你必须调用工具函数实际完成，不能仅用文字回复。")

        return "\n\n".join(sections)

    def _prepare_messages(self, user_message: str, canvas_context: dict = None,
                          memory_prompt: str = "", llm_client=None,
                          unified_result: dict = None, session_memory: str = "",
                          skill_context: dict = None, images: list = None) -> list:
        """Build the full message list for LLM.

        When images are provided, the latest user message is built as a
        multimodal content array (text + image_url blocks) compatible with
        OpenAI's vision / DeepSeek multimodal API.
        """
        system_content = self._build_system_prompt(
            user_message, canvas_context, memory_prompt, unified_result,
            session_memory=session_memory, skill_context=skill_context,
        )
        messages = [{"role": "system", "content": system_content}]

        if llm_client:
            self._compact_history(llm_client)
        else:
            self._trim_history()
        # Shallow-copy each history message to avoid mutating self.history
        messages.extend(dict(m) for m in self.history)

        # ── Vision bridge: preprocess images → text description ──
        # DeepSeek API 暂不支持 image_url multimodal 格式，采用旁路视觉模型桥接：
        #   图片 → VisionHandler (Qwen-VL / GPT-4o 等) → 文字描述 → 注入 user message
        has_images = bool(images)
        if has_images:
            vision_desc = self._describe_images(images)
            if vision_desc:
                # Find the last user message and prepend the vision description
                for i in range(len(messages) - 1, -1, -1):
                    if messages[i].get("role") == "user" and isinstance(messages[i].get("content"), str):
                        messages[i]["content"] = (
                            f"[系统提示] 用户在此消息中附带了 {len(images)} 张图片。"
                            f"以下是图片的视觉分析结果，请基于这些信息回答用户问题：\n\n"
                            f"{vision_desc}\n\n"
                            f"---\n用户消息：{messages[i]['content']}"
                        )
                        break

        return messages

    # ── V3 API ────────────────────────────────────────────────────────────

    @property
    def _engine(self):
        if not hasattr(self, "_engine_inst"):
            self._engine_inst = AgentEngine(get_llm_client(), self.user_id, AGENT_DEFAULT_MODEL)
        return self._engine_inst

    def chat_v3(self, user_message: str, canvas_context: dict = None,
                confirm_handler=None, model: str = AGENT_DEFAULT_MODEL,
                redis_client=None, task_id: str = "", stream: bool = False,
                images: list = None):
        """V3 unified agent chat — single LLM call for intent+plan, then execute.

        Args:
            images: Optional list of base64 data URL strings (data:image/...;base64,...)
                    for multimodal vision input.
        """

        # ── Input Guard (boundary defense) ──
        from app.util.agent.guard import InputGuard
        guard_result = InputGuard.check(user_message)
        if not guard_result["ok"]:
            yield {"type": "error", "data": {"message": guard_result.get("reason", "输入被安全策略拦截")}}
            yield {"type": "done", "data": {"status": "blocked"}}
            return

        # ── Restore cross-session memory (messages + prompt) ──
        session_memory_prompt = ""
        try:
            from app.util.agent.session_memory import SessionMemory
            restored = SessionMemory.restore(self.user_id)
            session_memory_prompt = restored.get("prompt", "")
            restored_msgs = restored.get("messages", [])
            if restored_msgs:
                self.history = list(restored_msgs)
        except Exception:
            logging.debug("SessionMemory restore skipped", exc_info=True)

        self.history.append({"role": "user", "content": user_message})

        # ── Plan-Feedback 闭环 ──
        plan_feedback_hints = ""
        try:
            from app.util.agent.plan_eval import PlanMemory
            tentative_domains = classify_domain(user_message)
            plan_feedback_hints = PlanMemory.get_hints_for_domains(tentative_domains)
            failure_hints = PlanMemory.get_failure_summary(limit=2)
            if failure_hints:
                plan_feedback_hints = plan_feedback_hints + "\n\n" + failure_hints if plan_feedback_hints else failure_hints
        except Exception:
            logging.debug("Plan feedback retrieval skipped", exc_info=True)

        # ── Unified LLM call: intent + domains + plan ──
        unified_result = unified_intent_and_plan(
            self._engine.llm, user_message, self.history[-6:], model,
            plan_feedback_hints=plan_feedback_hints,
        )

        skill_context = {"has_failures": False}

        messages = self._prepare_messages(
            user_message, canvas_context=canvas_context, llm_client=self._engine.llm,
            unified_result=unified_result, session_memory=session_memory_prompt,
            skill_context=skill_context, images=images,
        )

        # Delegate to engine
        for event in self._engine.chat(
            user_message=user_message, messages=messages, memory_prompt="",
            confirm_handler=confirm_handler, redis_client=redis_client,
            task_id=task_id, stream=stream,
            precomputed_plan=unified_result.get("plan"),
        ):
            if event[0] == "llm_response":
                choice = event[1]
                tool_count = event[2]
                content = choice.message.content or ""
                self.history.append({"role": "assistant", "content": content})
                if self._engine.llm:
                    self._compact_history(self._engine.llm)
                else:
                    self._trim_history()
                yield {"type": "message", "data": {"text": content, "tool_calls_made": tool_count}}
            else:
                evt = self._translate_event(event)
                if evt is not None:
                    yield evt
                    # ── References event: extract search/fetch results for citation display ──
                    if event[0] == "tool_result":
                        refs = self._extract_references(event[1], event[2], event[3])
                        if refs:
                            yield {"type": "references", "data": {"references": refs}}

        # Persist session memory
        self._persist_session()

    def _translate_event(self, event: tuple) -> dict | None:
        """Translate V3 engine event tuple to SSE dict format."""
        kind = event[0]
        if kind == "token":
            return {"type": "token", "data": {"text": event[1]}}
        elif kind == "tool_call":
            return {"type": "tool_call", "data": {"tool": event[1], "args": event[2]}}
        elif kind == "tool_result":
            from app.util.agent.helpers import sanitize_for_json
            try:
                safe_result = sanitize_for_json(event[3])
            except Exception:
                safe_result = str(event[3])[:1000]
            return {"type": "tool_result", "data": {"tool": event[1], "success": event[2], "result": safe_result}}
        elif kind == "plan":
            return {"type": "plan", "data": event[1]}
        elif kind == "step_start":
            return {"type": "step_start", "data": event[1]}
        elif kind == "step_end":
            return {"type": "step_end", "data": event[1]}
        elif kind == "step_fail":
            return {"type": "step_fail", "data": event[1]}
        elif kind == "confirm_required":
            return {"type": "confirm_required", "data": event[1]}
        elif kind == "progress":
            return {"type": "progress", "data": event[1]}
        elif kind == "done":
            return {"type": "done", "data": event[1]}
        elif kind == "error":
            return {"type": "error", "data": {"message": event[1]}}
        elif kind == "trace":
            return {"type": "trace", "data": event[1]}
        elif kind == "think":
            return {"type": "thinking", "data": {"content": event[1]}}
        return None

    @staticmethod
    def _extract_domain(url: str) -> str:
        """Extract domain from a URL."""
        import re
        m = re.match(r'https?://([^/]+)', url)
        return m.group(1).replace('www.', '') if m else ''

    @staticmethod
    def _clean_title(title: str, url: str) -> str:
        """Clean a search result title: strip domain prefixes, fix garbled text."""
        import re
        title = (title or "").strip()
        if not title:
            return AgentSession._extract_domain(url) if url else ""
        # Bing concatenation: "domain.comhttps://actual-url" — extract domain for title
        m = re.match(r'^([\w.-]+\.\w{2,6})https?://', title)
        if m:
            domain = m.group(1)
            # Use domain as fallback title
            title = re.sub(r'^[\w.-]+\.\w{2,6}https?://\S+', domain, title).strip()
        # Remove leading domain + breadcrumb arrow (e.g. "wikipedia.org › ")
        title = re.sub(r'^[\w.-]+\.\w{2,6}\s*[›»>]\s*', '', title).strip()
        # Strip pure URL prefixes
        title = re.sub(r'^https?://\S+\s*', '', title).strip()
        # Filter out garbled chars: replace U+FFFD, C1 controls, lone surrogates
        title = re.sub(r'[�\x80-\x9f\ud800-\udfff]', '', title).strip()
        if not title:
            domain = AgentSession._extract_domain(url)
            return domain if domain else url[:80]
        return title[:200]

    @staticmethod
    def _extract_references(tool_name: str, success: bool, result) -> list | None:
        """Extract citation references from web_search / web_fetch tool results.

        Returns a list of {title, url, snippet, domain} dicts, or None if
        no references can be extracted.
        """
        import re
        if not success or not isinstance(result, dict):
            return None
        data = result.get("data") or result
        if not isinstance(data, dict):
            return None

        if tool_name == "web_search":
            results = data.get("results", [])
            if not results:
                return None
            refs = []
            for r in results:
                url = r.get("url", "")
                if not url:
                    continue
                # Bing tracking URLs: extract real URL from "domain+URL" text pattern
                if "bing.com/ck/" in url:
                    raw_title = r.get("title", "")
                    m = re.match(r'^[\w.-]+\.\w{2,6}(https?://\S+)', raw_title)
                    if m:
                        url = m.group(1)
                        # Title becomes just the domain
                        title = AgentSession._extract_domain(url)
                    else:
                        title = AgentSession._clean_title(raw_title, url)
                else:
                    title = AgentSession._clean_title(r.get("title", ""), url)
                refs.append({
                    "title": title,
                    "url": url,
                    "snippet": (r.get("snippet", "") or "")[:300],
                    "domain": r.get("domain", "") or AgentSession._extract_domain(url),
                })
                if len(refs) >= 10:
                    break
            return refs if refs else None

        elif tool_name == "web_fetch":
            url = data.get("url", "")
            if not url:
                return None
            return [{
                "title": AgentSession._clean_title(data.get("title", ""), url),
                "url": url,
                "snippet": (data.get("content", "") or "")[:300],
                "domain": AgentSession._extract_domain(url),
            }]

        return None

    @staticmethod
    def _describe_images(images: list) -> str:
        """Preprocess images through vision model → text description (vision bridge)."""
        try:
            from app.util.vision import VisionHandler
            prompt = json.dumps({
                "task": "describe",
                "instructions": (
                    "请详细描述这张图片的内容。如果是图表/架构图/流程图，请描述其中的结构、节点、连接关系和文字标注。"
                    "如果是截图/照片，请描述场景、物体、文字和关键细节。"
                    "输出纯文本中文描述，不要用 JSON 格式。"
                ),
            }, ensure_ascii=False)
            ok, result = VisionHandler.analyze_images(images, prompt, task_type="describe")
            if ok:
                if isinstance(result, dict):
                    return result.get("description") or result.get("raw") or str(result)
                return str(result)
            return None
        except Exception:
            logging.debug("Vision bridge failed, proceeding text-only", exc_info=True)
            return None

    def clear_history(self):
        self.history = []
        self._compact_summary = ""

    def _persist_session(self):
        """Persist session memory for cross-session continuity."""
        try:
            from app.util.agent.session_memory import SessionMemory
            import uuid
            session_id = str(uuid.uuid4())[:8]
            summary = self._compact_summary if self._compact_summary else ""
            SessionMemory.persist(self.user_id, session_id, self.history, summary)
        except Exception:
            logging.debug("SessionMemory persist skipped", exc_info=True)
