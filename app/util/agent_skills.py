# -*- coding: UTF-8 -*-
"""Agent Skills — dynamic prompt injection per domain."""

# ── Domain Skill Templates ──────────────────────────────────────────────────

_CANVAS_SKILL = """## 画布编辑能力
你可以通过 canvas 工具在 2D 画布上创建和编辑图形，使用 action 参数选择操作：
- canvas(action="add_pen", type="...", x=..., y=..., text="..."): 创建图形（rectangle/circle/triangle/diamond/pentagon/star/text/image）
- canvas(action="add_line", from_pen="...", to_pen="...", text="..."): 创建连线（straight/curve/polyline/mind，支持箭头）
- canvas(action="update_pen", pen_id="...", props={...}): 修改图形属性（位置、大小、颜色、文字等）
- canvas(action="delete_pen", pen_id="..." 或 pen_ids=[...]): 删除图形
- canvas(action="get_state"): 查看画布状态
- canvas(action="undo"/"redo"): 撤销/重做
- canvas(action="clear", confirm=true): 清空画布
- 布局排版：layout_auto_arrange、layout_align"""

_BLUEPRINT_SKILL = """## 蓝图管理能力
你可以管理蓝图（保存的画布快照）：
- blueprint_list: 列出所有蓝图（支持分页和关键词筛选）
- blueprint_search: 按关键词搜索蓝图
- blueprint_load: 加载蓝图到画布（替换当前内容）
- blueprint_save: 将当前画布保存为蓝图
- blueprint_export: 导出为 PNG/SVG/JSON 格式"""

_FILE_SKILL = """## 文件管理能力
你可以搜索文件管理器中的素材和文件：
- file_search: 按关键词和类型（image/svg/document）搜索文件
- 支持图片、SVG、文档等多种格式"""

_MINDMAP_SKILL = """## 思维导图能力
你可以创建和编辑思维导图：
- 使用 ```mindmap 格式输出标准 Markdown 无序列表
- 每行一项，缩进表示层级
- 根主题 → 分支 → 细节节点
- 使用 mind 曲线连接节点"""

_CODE_SKILL = """## 代码生成能力
你可以生成 JavaScript/JSON 代码片段：
- code_generate: 根据描述生成代码
- 支持 Monaco 编辑器可直接使用的格式"""

_MAP_SKILL = """## 地图与位置能力
你可以帮助用户查询地理位置和规划路线：
- geocode(address="地点名"): 地名转经纬度坐标
- regeocode(lng=..., lat=...): 坐标转地址
- ```map 代码块: 在地图上展示位置标记
- ```route 代码块: 显示两地之间的路线规划"""

_GENERAL_SKILL = """## 通用能力
- 画布图形编辑（创建、修改、删除、连线、布局）
- 蓝图管理（保存、加载、搜索、导出）
- 文件搜索
- 代码生成
- 地图查询与路线规划"""

# ── Skill Selector ──────────────────────────────────────────────────────────

_DOMAIN_SKILLS = {
    "canvas": _CANVAS_SKILL,
    "blueprint": _BLUEPRINT_SKILL,
    "file": _FILE_SKILL,
    "mindmap": _MINDMAP_SKILL,
    "code": _CODE_SKILL,
    "map": _MAP_SKILL,
    "general": _GENERAL_SKILL,
}


def get_skills_for_intent(domains: list[str] = None, context: dict = None) -> str:
    """Return skill prompt text for the given domains.

    Args:
        domains: Domain tags from classify_domain() or unified_intent_and_plan().
                 e.g. ["canvas", "blueprint"]
        context: Optional dict with keys like "has_failures".

    Returns:
        Multi-line skill prompt string to inject into the system message.
    """
    tags = domains or ["general"]
    if not tags or tags == ["general"]:
        return ""

    sections = ["## 当前可用能力"]
    seen = set()
    for tag in tags:
        if tag in seen:
            continue
        seen.add(tag)
        skill_text = _DOMAIN_SKILLS.get(tag)
        if skill_text:
            sections.append(skill_text)

    if context and context.get("has_failures"):
        sections.append("\n[!] 注意：之前的操作遇到了失败，请更谨慎地选择工具和参数。")

    if len(sections) == 1:
        return ""
    return "\n\n".join(sections)
