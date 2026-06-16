# -*- coding: UTF-8 -*-
"""AgentDispatcher — sub-agent registry, tool schema generation, and routing."""

import logging
import threading
import time
from concurrent.futures import TimeoutError as FutureTimeoutError

from app.config import LLM_TIMEOUT
from app.util.agents import get_all_agents
from app.util.agents.base import AgentBase
from app.util.executor import ManagedPool

_SUB_AGENT_TIMEOUT = 120
_MAX_CONCURRENT_DISPATCH = 3
_PEER_QUERY_TIMEOUT = 15
_dispatch_semaphore = threading.BoundedSemaphore(_MAX_CONCURRENT_DISPATCH)
_dispatch_pool = ManagedPool(max_workers=_MAX_CONCURRENT_DISPATCH, prefix="subagent-")


class AgentDispatcher:
    """Registry and router for sub-agents. Exposes dispatch_agent as a function-calling tool."""

    def __init__(self):
        self._agents: dict[str, AgentBase] = {}
        for agent in get_all_agents():
            self.register(agent)

    def register(self, agent: AgentBase):
        self._agents[agent.name] = agent
        logging.info("AgentDispatcher registered: %s", agent.name)

    @property
    def agent_names(self) -> list:
        return list(self._agents.keys())

    def get_dispatch_tool_schema(self) -> dict:
        if not self._agents:
            return None
        agent_list = "\n".join(f"- {name}: {ag.description}" for name, ag in self._agents.items())
        return {
            "type": "function",
            "function": {
                "name": "dispatch_agent",
                "description": f"将子任务派发给专业子 Agent 执行。可用子 Agent:\n{agent_list}",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "agent_name": {"type": "string", "enum": list(self._agents.keys()), "description": "要调用的子 Agent 名称"},
                        "task": {"type": "string", "description": "给子 Agent 的详细任务描述，包含所有必要上下文"},
                    },
                    "required": ["agent_name", "task"],
                },
            },
        }

    def get_peer_query_tool_schema(self) -> dict:
        if not self._agents:
            return None
        agent_list = "\n".join(f"- {name}: {ag.description}" for name, ag in self._agents.items())
        return {
            "type": "function",
            "function": {
                "name": "ask_peer",
                "description": f"向其他专业 Agent 询问信息（一问一答，轻量查询）。可用 Agent:\n{agent_list}",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "agent_name": {"type": "string", "enum": list(self._agents.keys()), "description": "要询问的 Agent 名称"},
                        "question": {"type": "string", "description": "具体问题，包含必要的上下文信息"},
                    },
                    "required": ["agent_name", "question"],
                },
            },
        }

    def handle_peer_query(self, llm_client, agent_name: str, question: str,
                          tool_context: dict, model: str = "deepseek-chat", tracer=None) -> dict:
        agent = self._agents.get(agent_name)
        if not agent:
            return {"success": False, "result": f"未知 Agent: {agent_name}，可用: {', '.join(self._agents.keys())}"}
        caller_name = tool_context.get("_caller_agent", "")
        if caller_name == agent_name:
            return {"success": False, "result": f"不能询问自己（{agent_name}），请直接使用已有知识或工具"}

        messages = [{"role": "system", "content": agent.system_prompt}]
        pheromone = tool_context.get("_pheromone", "")
        if pheromone:
            messages.append({"role": "system", "content": f"当前上下文已知信息:\n{pheromone}"})
        messages.append({"role": "user", "content": f"同事 Agent 询问：{question}\n\n请简洁回答（不要调用工具，仅基于你的专业知识回答）。"})

        try:
            if tracer:
                psid = tracer.start_span(f"peer_query:{agent_name}", input={"question": question[:200], "from": caller_name})
            resp = llm_client.chat.completions.create(
                model=model, messages=messages, temperature=0, max_tokens=512, timeout=_PEER_QUERY_TIMEOUT,
            )
            content = resp.choices[0].message.content or ""
            if tracer:
                tracer.end_span(psid, "ok", {"result": content[:200]})
            return {"success": True, "result": content}
        except Exception as ex:
            logging.warning("Peer query to %s failed: %s", agent_name, ex)
            if tracer:
                tracer.end_span(psid, "error", {"error": str(ex)})
            return {"success": False, "result": f"向 {agent_name} 查询失败: {ex}"}

    def dispatch(self, llm_client, agent_name: str, task: str, tool_context: dict,
                 model: str = "deepseek-chat", tracer=None) -> dict:
        agent = self._agents.get(agent_name)
        if not agent:
            return {"success": False, "result": f"未知 Agent: {agent_name}", "tool_calls_made": 0}

        acquired = _dispatch_semaphore.acquire(timeout=30)
        if not acquired:
            return {"success": False, "result": "子 Agent 调度过载，请稍后重试", "tool_calls_made": 0}

        cancel_event = threading.Event()
        ctx = {**tool_context, "_cancel_event": cancel_event}
        future = None
        try:
            logging.info("AgentDispatcher dispatching to %s: %s", agent_name, task[:100])
            future = _dispatch_pool.get().submit(agent.run, llm_client, task, ctx, model, tracer=tracer, dispatcher=self)
            return future.result(timeout=_SUB_AGENT_TIMEOUT)
        except FutureTimeoutError:
            logging.warning("Sub-agent %s timed out after %ds", agent_name, _SUB_AGENT_TIMEOUT)
            cancel_event.set()
            if future:
                future.cancel()
            return {"success": False, "result": f"子 Agent {agent_name} 执行超时（{_SUB_AGENT_TIMEOUT}秒）", "tool_calls_made": 0}
        except Exception as ex:
            logging.exception("Sub-agent %s dispatch error", agent_name)
            cancel_event.set()
            if future:
                future.cancel()
            return {"success": False, "result": f"子 Agent 调度异常: {ex}", "tool_calls_made": 0}
        finally:
            _dispatch_semaphore.release()
