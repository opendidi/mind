# -*- coding: UTF-8 -*-
"""FileAgent — 文件/素材检索子 Agent。"""

from app.util.agents.base import AgentBase
from app.util.agent_tools import TOOL_SCHEMAS

FILE_TOOLS = ["file_search"]


class FileAgent(AgentBase):
    name = "file_agent"
    description = "文件素材管理专家，负责搜索和查找文件资源。"

    system_prompt = """你是文件素材管理专家，负责帮助用户查找和管理文件资源。

## 职责
- 搜索文件管理器中的素材/文件
- 帮助用户找到需要的图片、SVG、文档等资源

## 核心工具
- file_search: 按关键词和类型搜索文件

## 最佳实践
1. 使用明确的关键词搜索
2. 可以通过 type 参数筛选文件类型（image/svg/document）
"""

    @property
    def tools(self):
        return [s for s in TOOL_SCHEMAS
                if s.get("function", {}).get("name") in FILE_TOOLS]
