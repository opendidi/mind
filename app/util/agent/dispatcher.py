# -*- coding: UTF-8 -*-
"""AgentDispatcher — sub-agent registry, tool schema generation, and routing."""

import atexit as _atexit
import logging
import threading
import time
from concurrent.futures import TimeoutError as FutureTimeoutError

from app.config import AGENT_DEFAULT_MODEL, LLM_TIMEOUT
from app.util.agent.agents import get_all_agents
from app.util.agent.agents.base import AgentBase
from app.util.agent.constants import MAX_CONCURRENT_DISPATCH as _MAX_CONCURRENT_DISPATCH
from app.util.agent.constants import PEER_QUERY_TIMEOUT as _PEER_QUERY_TIMEOUT
from app.util.agent.constants import SUB_AGENT_TIMEOUT as _SUB_AGENT_TIMEOUT
from app.util.executor import ManagedPool

_dispatch_semaphore = threading.BoundedSemaphore(_MAX_CONCURRENT_DISPATCH)
_dispatch_pool = ManagedPool(max_workers=_MAX_CONCURRENT_DISPATCH, prefix="subagent-")


@_atexit.register
def _shutdown_dispatch_pool():
    """Clean up dispatch thread pool on application exit."""
    pool = _dispatch_pool._pool
    if pool and not getattr(pool, "_shutdown", 0):
        pool.shutdown(wait=False)


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

    def build_agent_list(self) -> str:
        """Build a formatted agent list string for Supervisor prompt injection."""
        return "\n".join(f"- {name}: {ag.description}" for name, ag in self._agents.items())

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
                        "agent_name": {
                            "type": "string",
                            "enum": list(self._agents.keys()),
                            "description": "要调用的子 Agent 名称",
                        },
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
                        "agent_name": {
                            "type": "string",
                            "enum": list(self._agents.keys()),
                            "description": "要询问的 Agent 名称",
                        },
                        "question": {"type": "string", "description": "具体问题，包含必要的上下文信息"},
                    },
                    "required": ["agent_name", "question"],
                },
            },
        }

    def handle_peer_query(
        self,
        llm_client,
        agent_name: str,
        question: str,
        tool_context: dict,
        model: str = AGENT_DEFAULT_MODEL,
        tracer=None,
    ) -> dict:
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
        messages.append(
            {
                "role": "user",
                "content": f"同事 Agent 询问：{question}\n\n请简洁回答（不要调用工具，仅基于你的专业知识回答）。",
            }
        )

        from app.util.agent.retry import retry_llm_call

        psid = None
        if tracer:
            psid = tracer.start_span(
                f"peer_query:{agent_name}", input={"question": question[:200], "from": caller_name}
            )
        try:
            resp = retry_llm_call(
                lambda: llm_client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=0,
                    max_tokens=512,
                    timeout=_PEER_QUERY_TIMEOUT,
                ),
                max_retries=3,
            )
            content = resp.choices[0].message.content or ""
            if tracer:
                tracer.end_span(psid, "ok", {"result": content[:200]})
            return {"success": True, "result": content}
        except Exception as ex:
            logging.warning("Peer query to %s failed: %s", agent_name, ex)
            if tracer:
                tracer.end_span(psid, "error", {"error": str(ex)[:100]})
            return {"success": False, "result": f"向 {agent_name} 查询失败（重试后仍失败）"}

    def dispatch(
        self,
        llm_client,
        agent_name: str,
        task: str,
        tool_context: dict,
        model: str = AGENT_DEFAULT_MODEL,
        tracer=None,
        event_queue=None,
        stream: bool = False,
    ) -> dict:
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
            future = _dispatch_pool.get().submit(
                agent.run,
                llm_client,
                task,
                ctx,
                model,
                tracer=tracer,
                dispatcher=self,
                event_queue=event_queue,
                stream=stream,
            )
            return future.result(timeout=_SUB_AGENT_TIMEOUT)
        except FutureTimeoutError:
            logging.warning("Sub-agent %s timed out after %ds", agent_name, _SUB_AGENT_TIMEOUT)
            cancel_event.set()
            if future:
                future.cancel()
            return {
                "success": False,
                "result": f"子 Agent {agent_name} 执行超时（{_SUB_AGENT_TIMEOUT}秒）",
                "tool_calls_made": 0,
            }
        except Exception as ex:
            logging.exception("Sub-agent %s dispatch error", agent_name)
            cancel_event.set()
            if future:
                future.cancel()
            return {"success": False, "result": f"子 Agent 调度异常: {ex}", "tool_calls_made": 0}
        finally:
            if acquired:
                _dispatch_semaphore.release()

    # ── Multi-Agent Negotiation (Phase 2) ─────────────────────────────────

    def negotiate(
        self,
        llm_client,
        task: str,
        proposing_agents: list = None,
        tool_context: dict = None,
        model: str = AGENT_DEFAULT_MODEL,
        rounds: int = None,
        tracer=None,
    ) -> dict:
        """Phase 2: 多 Agent 协商 — 多方案评审、冲突解决、最优解选择。

        流程：
            1. 每个 Agent 独立提出方案
            2. 互相评审（每个 Agent 评审其他 Agent 的方案）
            3. 投票选最优方案
            4. 最多 rounds 轮

        Args:
            llm_client: LLM 客户端
            task: 任务描述
            proposing_agents: 参与协商的 Agent 名列表，默认所有已注册 Agent
            tool_context: 工具上下文
            model: LLM 模型
            rounds: 最多协商轮数
            tracer: 追踪器

        Returns:
            dict: {consensus, result, agent_votes, rounds_completed}
        """
        from app.util.agent.constants import CONSENSUS_THRESHOLD, NEGOTIATION_ROUNDS, NEGOTIATION_TIMEOUT

        max_rounds = rounds or NEGOTIATION_ROUNDS
        agent_names = proposing_agents or self.agent_names
        if not agent_names:
            return {"consensus": False, "result": "无可用的协商 Agent", "agent_votes": {}, "rounds_completed": 0}

        if len(agent_names) < 2:
            # 单个 Agent 无需协商，直接委托
            result = self.dispatch(llm_client, agent_names[0], task, tool_context or {}, model, tracer, None, False)
            return {
                "consensus": True,
                "result": result.get("result", ""),
                "agent_votes": {agent_names[0]: 1.0},
                "rounds_completed": 1,
            }

        proposals: dict = {}  # {agent_name: proposal_text}
        votes: dict = {}  # {agent_name: score}

        for round_num in range(1, max_rounds + 1):
            logging.info("Negotiation round %d/%d for task: %s", round_num, max_rounds, task[:80])

            # 1. 各 Agent 提出/修订方案
            for agent_name in agent_names:
                if round_num == 1:
                    # 首轮：每个 Agent 独立提出方案
                    propose_prompt = (
                        f"请针对以下任务提出你的解决方案（简洁、可执行）：\n\n{task}\n\n"
                        f"请直接给出方案，不需要询问更多信息。"
                    )
                    result = self.dispatch(
                        llm_client, agent_name, propose_prompt, tool_context or {}, model, tracer, None, False
                    )
                    if result.get("success"):
                        proposals[agent_name] = result.get("result", "")
                else:
                    # 后续轮：基于他人评审修订方案
                    other_proposals = {k: v for k, v in proposals.items() if k != agent_name}
                    critique_text = "\n\n".join(f"Agent {k} 的方案:\n{v[:500]}" for k, v in other_proposals.items())
                    revise_prompt = (
                        f"任务: {task}\n\n你的原始方案:\n{proposals.get(agent_name, '')[:500]}\n\n"
                        f"其他 Agent 的方案:\n{critique_text}\n\n"
                        f"请综合考虑各方案优点，修订你的方案（简洁、可执行）。"
                    )
                    result = self.dispatch(
                        llm_client, agent_name, revise_prompt, tool_context or {}, model, tracer, None, False
                    )
                    if result.get("success"):
                        proposals[agent_name] = result.get("result", "")

            # 2. 互相评审 + 投票
            for voter_name in agent_names:
                total_score = 0.0
                candidates = [n for n in agent_names if n != voter_name]
                if not candidates:
                    continue
                for candidate in candidates:
                    candidate_proposal = proposals.get(candidate, "")
                    if not candidate_proposal:
                        continue
                    critique_prompt = (
                        f"任务: {task}\n\n候选方案 (Agent {candidate}):\n{candidate_proposal[:800]}\n\n"
                        f'请评分（0.0-1.0）并简要点评。输出 JSON: {{"score": 0.0-1.0, "comment": "点评"}}'
                    )
                    peer_result = self.handle_peer_query(
                        llm_client, voter_name, critique_prompt, tool_context or {}, model, tracer
                    )
                    if peer_result.get("success"):
                        try:
                            critique_data = json.loads(
                                extract_json(peer_result.get("result", "{}")) or "{}"
                            )
                            total_score += float(critique_data.get("score", 0.5))
                        except (json.JSONDecodeError, ValueError, TypeError):
                            total_score += 0.5

                # 归一化
                score = total_score / max(len(candidates), 1)
                votes[voter_name] = votes.get(voter_name, 0.0) + score

            # 3. 检查共识
            max_score = max(votes.values()) if votes else 0
            consensus_agent = max(votes, key=votes.get) if votes else None

            if max_score >= CONSENSUS_THRESHOLD and consensus_agent:
                logging.info(
                    "Negotiation: consensus reached at round %d — %s (score=%.2f)",
                    round_num,
                    consensus_agent,
                    max_score,
                )
                return {
                    "consensus": True,
                    "result": proposals.get(consensus_agent, ""),
                    "agent_votes": votes,
                    "rounds_completed": round_num,
                    "winning_agent": consensus_agent,
                }

        # 未达共识 — 返回得分最高的方案
        best_agent = max(votes, key=votes.get) if votes else (agent_names[0] if agent_names else None)
        return {
            "consensus": False,
            "result": proposals.get(best_agent, "") if best_agent else "",
            "agent_votes": votes,
            "rounds_completed": max_rounds,
            "winning_agent": best_agent,
        }


# Import for negotiation JSON extraction
def extract_json(text: str) -> str | None:
    """Extract JSON from text (simple bracket matching)."""
    import re
    if not text:
        return None
    match = re.search(r'\{[^{}]*\}', text, re.DOTALL)
    return match.group(0) if match else None
