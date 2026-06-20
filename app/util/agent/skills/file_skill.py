# -*- coding: UTF-8 -*-
"""File skill — 文件管理领域知识。"""

FILE_SKILL = """## 文件管理指南

### 支持的素材类型
| 类型 | 扩展名 | 用途 |
|------|--------|------|
| 图片 | .png .jpg .jpeg .gif .webp .svg | 插图、图标、背景 |
| 文档 | .json .txt .md | 数据文件、配置 |
| 表格 | .xlsx .xls | Excel 数据分析与图表生成 |

### Excel 数据分析与图表
使用 `extract_excel` 工具解析 Excel 文件后，可以从数据生成 ECharts 图表。

**图表生成方法**：在回复中使用 ```chart 代码块，格式如下：
```chart
{
  "option": <ECharts 标准 option 对象>,
  "height": "400px"
}
```

支持的图表类型（option 中的 series.type）：
- line: 折线图
- bar: 柱状图
- pie: 饼图
- scatter: 散点图
- area: 面积图（line + areaStyle）

示例 — 从 Excel 销售数据生成柱状图：
```chart
{
  "option": {
    "title": { "text": "月度销售统计" },
    "tooltip": {},
    "xAxis": { "type": "category", "data": ["1月", "2月", "3月", "4月"] },
    "yAxis": { "type": "value" },
    "series": [{ "type": "bar", "data": [120, 200, 150, 80] }]
  },
  "height": "360px"
}
```

### 搜索技巧
- 使用文件名关键词搜索
- 可通过 type 参数筛选：image / svg / document
- 不指定 type 则搜索所有文件
"""
