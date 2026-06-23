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
- 布局排版：layout_auto_arrange、layout_align

[!] 创建新图形时，请将 x/y 设置为画布上下文中 viewportCenter 附近的值（±200 范围），确保图形出现在用户可见区域。不要使用 (0,0) 或随机的坐标。"""

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
- 支持图片、SVG、文档等多种格式

### 图片分析与 OCR
当用户要求识别/分析文件管理器中的图片时：
1. 使用 file_search 搜索图片，获取结果中的 url 字段
2. 调用 analyze_image(image_url=url, task_type="...") 分析图片

analyze_image task_type：
- ocr: 提取图片中的文字，支持中英文，自动识别表格
- describe: 场景描述，获取图片内容、物体、关键词
- detect: 物体检测，返回物体名称和位置
- classify: 智能分类

输入方式（三选一）：image_url（file_search 返回的 url 字段）/ object_name（MinIO路径）/ image_base64

### Excel 数据分析与图表
当用户上传 Excel 文件（.xlsx/.xls）并要求分析时：
1. 使用 `extract_excel` 工具解析文件数据
2. 分析数据结构，选择合适的图表类型
3. 在回复中使用 ```chart 代码块输出 ECharts 图表

图表格式（JSON）：
```chart
{
  "option": { "title": {"text":"标题"}, "xAxis": {"type":"category","data":[...]}, "yAxis": {"type":"value"}, "series": [{"type":"bar","data":[...]}] },
  "height": "400px"
}
```

支持的图表类型：bar（柱状图）、line（折线图）、pie（饼图）、scatter（散点图）
- 数据对比 → bar
- 趋势变化 → line
- 占比分布 → pie
- 相关性 → scatter"""

_MINDMAP_SKILL = """## 思维导图能力
你可以生成思维导图，**必须使用 ```mindmap 代码块输出，不要用 canvas 工具**：
- 输出标准 Markdown 无序列表，每行一项，2空格缩进
- 根主题 → 分支 → 细节节点
- 前端会通过 markmap 渲染为 SVG 树图"""

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
- 图片分析（场景描述、物体检测、智能分类、OCR 文字提取）
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
