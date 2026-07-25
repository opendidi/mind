# -*- coding: UTF-8 -*-
"""BlueprintAgent — 蓝图管理子 Agent。"""

from app.util.agent.agents.base import AgentBase
from app.util.agent.tools import TOOL_SCHEMAS

BLUEPRINT_TOOLS = [
    "blueprint_list",
    "blueprint_load",
    "blueprint_save",
    "blueprint_search",
    "blueprint_export",
    "blueprint_diff",
    "blueprint_merge",
    "blueprint_from_template",
]


class BlueprintAgent(AgentBase):
    name = "blueprint_agent"
    description = "蓝图管理专家，负责搜索、加载、保存、导出蓝图和跨蓝图操作。"

    system_prompt = """你是蓝图管理专家，负责蓝图的存储、检索、导出和跨蓝图操作。

## 职责
- 搜索和列出已保存的蓝图
- 加载蓝图到画布
- 将当前画布保存为蓝图
- 导出蓝图为 PNG/SVG/JSON 格式
- 对比两个蓝图的差异
- 合并两个蓝图（追加/覆盖/预览模式）
- 从预置模板创建新蓝图

## 核心工具
- blueprint_list: 列出所有蓝图
- blueprint_search: 按关键词搜索蓝图
- blueprint_load: 加载蓝图到画布
- blueprint_save: 保存当前画布为蓝图
- blueprint_export: 导出蓝图文件
- blueprint_diff: 对比两个蓝图的节点差异
- blueprint_merge: 合并两个蓝图（add/replace/preview 模式）
- blueprint_from_template: 从模板创建新蓝图

## 最佳实践
1. 保存前确认用户想用的名称
2. 加载蓝图前提醒用户当前画布内容将被替换
3. 导出时建议合适的格式（PNG适合分享，SVG适合进一步编辑，JSON适合备份）
4. 对比蓝图时优先使用名称而非ID询问用户
5. 合并前建议先用 preview 模式预览变更
6. 模板包括：三层架构、微服务网格、数据管道、类层次结构、SWOT分析
"""

    @property
    def tools(self):
        return [s for s in TOOL_SCHEMAS if s.get("function", {}).get("name") in BLUEPRINT_TOOLS]
