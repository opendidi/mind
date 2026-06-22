# -*- coding: UTF-8 -*-
"""CodeAgent — 代码生成子 Agent。"""

from app.util.agent.agents.base import AgentBase
from app.util.agent.tools import TOOL_SCHEMAS

CODE_TOOLS = ["code_generate"]


class CodeAgent(AgentBase):
    name = "code_agent"
    description = "代码生成专家，根据描述生成 JavaScript/JSON 代码片段。"

    system_prompt = """你是代码生成专家，负责根据用户描述生成代码片段。

## 职责
- 根据描述生成 JavaScript 代码（可用于 Monaco 编辑器中的脚本）
- 生成 JSON 配置或数据

## 核心工具
- code_generate: 根据描述生成代码

## 最佳实践
1. JavaScript 代码应包含清晰的注释
2. JSON 结构应完整有效
3. 生成的代码应符合 mind 编辑器的上下文环境
"""

    @property
    def tools(self):
        return [s for s in TOOL_SCHEMAS if s.get("function", {}).get("name") in CODE_TOOLS]
