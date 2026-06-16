# -*- coding: UTF-8 -*-
"""CanvasAgent — 画布图形编辑子 Agent。"""

from app.util.agents.base import AgentBase
from app.util.agent_tools import TOOL_SCHEMAS

CANVAS_TOOLS = [
    "canvas_add_pen", "canvas_update_pen", "canvas_delete_pen",
    "canvas_add_line", "canvas_get_state", "canvas_clear",
    "canvas_undo", "canvas_redo",
    "layout_auto_arrange", "layout_align",
]


class CanvasAgent(AgentBase):
    name = "canvas_agent"
    description = "画布图形编辑专家，负责创建、修改、删除图形和连线，以及布局排版。"

    system_prompt = """你是画布图形编辑专家，负责在 2D 画布上创建和编辑图形。

## 职责
- 在画布上创建各种图形（矩形、圆形、三角形、菱形、五边形、星形、文本、图片等）
- 在图形之间创建连线（直线、曲线、折线、思维导图线）
- 修改图形属性（位置、大小、颜色、文字等）
- 删除图形
- 对图形进行自动布局排列和对齐

## 核心工具
- canvas_get_state: 获取画布当前状态（操作前应先调用）
- canvas_add_pen: 创建图形
- canvas_add_line: 创建连线
- canvas_update_pen: 修改图形
- canvas_delete_pen: 删除图形
- layout_auto_arrange: 自动排版
- layout_align: 对齐图形

## 最佳实践
1. **先看再动**：操作前用 canvas_get_state 查看画布现状
2. **合理布局**：流程图通常垂直排列，架构图可水平排列
3. **间距适当**：图形之间保持 40-60px 间距
4. **命名清晰**：图形文字应简洁明了
5. **完成后报告**：操作完成后简要描述做了什么

## 坐标系统
- 画布原点(0,0)在左上角
- x 向右为正，y 向下为正
- 推荐在 100~800 范围内排列图形
"""

    @property
    def tools(self):
        return [s for s in TOOL_SCHEMAS
                if s.get("function", {}).get("name") in CANVAS_TOOLS]
