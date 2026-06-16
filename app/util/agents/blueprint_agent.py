# -*- coding: UTF-8 -*-
"""BlueprintAgent — 蓝图管理子 Agent。"""

from app.util.agents.base import AgentBase
from app.util.agent_tools import TOOL_SCHEMAS

BLUEPRINT_TOOLS = [
    "blueprint_list", "blueprint_load", "blueprint_save",
    "blueprint_search", "blueprint_export",
]


class BlueprintAgent(AgentBase):
    name = "blueprint_agent"
    description = "蓝图管理专家，负责搜索、加载、保存和导出蓝图。"

    system_prompt = """你是蓝图管理专家，负责蓝图的存储、检索和导出。

## 职责
- 搜索和列出已保存的蓝图
- 加载蓝图到画布
- 将当前画布保存为蓝图
- 导出蓝图为 PNG/SVG/JSON 格式

## 核心工具
- blueprint_list: 列出所有蓝图
- blueprint_search: 按关键词搜索蓝图
- blueprint_load: 加载蓝图到画布
- blueprint_save: 保存当前画布为蓝图
- blueprint_export: 导出蓝图文件

## 最佳实践
1. 保存前确认用户想用的名称
2. 加载蓝图前提醒用户当前画布内容将被替换
3. 导出时建议合适的格式（PNG适合分享，SVG适合进一步编辑，JSON适合备份）
"""

    @property
    def tools(self):
        return [s for s in TOOL_SCHEMAS
                if s.get("function", {}).get("name") in BLUEPRINT_TOOLS]
