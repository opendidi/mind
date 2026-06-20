# -*- coding: UTF-8 -*-
"""Canvas skill — 画布图形编辑与图表生成领域知识。"""

CANVAS_SKILL = """## 画布图形编辑指南

### 图形类型
- **rectangle** — 矩形，适合表示流程步骤、组件框
- **circle** — 圆形，适合表示开始/结束节点
- **triangle** — 三角形，适合表示警告/注意
- **diamond** — 菱形，适合表示判断/条件分支
- **pentagon** — 五边形
- **star** — 星形
- **text** — 纯文字标签
- **image** — 图片

### 连线类型
- **straight** — 直线
- **curve** — 贝塞尔曲线
- **polyline** — 折线（多段直线）
- **mind** — 思维导图曲线（圆角）

### 箭头方向
- **start** — 起点箭头
- **end** — 终点箭头（最常用）
- **both** — 双向箭头
- **none** — 无箭头

### 生成完整图表（推荐使用 add_diagram）
当需要创建包含多个节点和连线的图表时，**优先使用 canvas action="add_diagram"** 一次性批量创建。
在 diagram 参数中定义所有节点和连线，避免多次调用。

#### 节点规格（nodes 数组中每个元素）
- **id**: 节点唯一标识（字符串，如 "start" / "step1" / "end"）
- **type**: 图形类型（rectangle/circle/diamond 等）
- **text**: 显示文字
- **x, y**: 位置坐标
- **width, height**: 宽高（默认 120x60）
- **background**: 背景色（可选，有默认配色）

#### 连线规格（edges 数组中每个元素）
- **from**: 起始节点 id
- **to**: 目标节点 id
- **text**: 连线标签（可选）
- **line_type**: straight/curve/polyline/mind
- **arrow**: start/end/both/none

#### 流程图示例
```
canvas(action="add_diagram", diagram={
  "nodes": [
    {"id":"start","type":"circle","text":"开始","x":250,"y":20,"width":80,"height":80},
    {"id":"login","type":"rectangle","text":"用户登录","x":200,"y":140},
    {"id":"check","type":"diamond","text":"验证通过?","x":200,"y":240,"width":130,"height":80},
    {"id":"home","type":"rectangle","text":"进入首页","x":200,"y":360},
    {"id":"error","type":"rectangle","text":"显示错误","x":400,"y":360},
    {"id":"end","type":"circle","text":"结束","x":250,"y":460,"width":80,"height":80}
  ],
  "edges": [
    {"from":"start","to":"login"},
    {"from":"login","to":"check"},
    {"from":"check","to":"home","text":"是"},
    {"from":"check","to":"error","text":"否"},
    {"from":"home","to":"end"},
    {"from":"error","to":"end"}
  ]
})
```

#### 架构图示例
```
canvas(action="add_diagram", diagram={
  "nodes": [
    {"id":"lb","type":"rectangle","text":"负载均衡","x":200,"y":50},
    {"id":"api1","type":"rectangle","text":"API 服务 1","x":80,"y":180},
    {"id":"api2","type":"rectangle","text":"API 服务 2","x":300,"y":180},
    {"id":"db","type":"rectangle","text":"MySQL","x":120,"y":310,"background":"#d1fae5","color":"#065f46"},
    {"id":"redis","type":"rectangle","text":"Redis","x":280,"y":310,"background":"#fef3c7","color":"#92400e"}
  ],
  "edges": [
    {"from":"lb","to":"api1"},
    {"from":"lb","to":"api2"},
    {"from":"api1","to":"db"},
    {"from":"api1","to":"redis"},
    {"from":"api2","to":"db"},
    {"from":"api2","to":"redis"}
  ]
})
```

### 布局参考
| 图表类型 | 排列方向 | 间距 | 起点坐标 |
|---------|---------|------|---------|
| 流程图   | 垂直    | 100px | x=200, y=20 |
| 架构图   | 水平+垂直 | 120px | x=50, y=50 |
| 思维导图 | 放射状  | 80px | x=400, y=300 |
| 拓扑图   | 均匀分布 | 100px | x=100, y=50 |

### 坐标参考
- 画布原点(0,0)在左上角
- x轴向右增加，y轴向下增加
- 单个图形默认尺寸: 120x60 (矩形), 80x80 (圆形/菱形)
"""
