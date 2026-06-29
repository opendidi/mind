# Chat Outline — 聊天文档大纲

## 概述

在聊天页面右侧新增 Outline 面板，按消息分组聚合 AI 回复中的 Markdown 标题（H1~H6），支持搜索过滤、点击定位、自动高亮，提升长文档阅读体验。

## 使用场景

用户与 AI 进行长文档类对话（如让 AI 生成项目文档、技术方案、API 设计等），AI 回复中包含大量 Markdown 标题。Outline 帮助用户快速定位章节，无需手动滚动查找。

## 功能范围

### v1 必须实现

| 功能 | 说明 |
|------|------|
| 标题解析 | 从渲染后的 DOM 中提取 H1~H6，自动注入 id 用于定位 |
| 按消息分组 | 标题树按消息分组，组头显示消息摘要 |
| 点击定位 | 点击标题 → 对应 heading `scrollIntoView({ behavior: 'smooth', block: 'start' })` |
| 自动高亮 | IntersectionObserver 追踪当前可见章节，Outline 中高亮对应项 |
| 搜索过滤 | 顶部搜索框实时过滤标题（忽略大小写、支持中文） |
| 流式去抖 | AI 流式输出时 300ms 防抖，避免频繁重建树 |
| 深色模式 | 跟随 `useTheme()` 切换样式 |
| 空状态 | 无标题时显示引导文案 |
| 键盘导航 | ↑↓ 移动焦点、Enter 跳转、Esc 关闭搜索 |
| 响应式 | 桌面端固定右侧面板；移动端通过顶部按钮唤出 Drawer |
| Canvas 互斥 | 默认显示 Outline；Agent 修改画布时自动切换到 Canvas 预览，用户可手动切换 |

### v1 不做

- AI 章节摘要/问答/思维导图联动
- PDF/Word Outline
- 面包屑导航
- 阅读进度追踪
- URL hash 同步（聊天场景无独立 URL）

## 架构设计

### 组件树

```
chat/index.vue
├── ChatSidebar          (左侧对话列表)
├── chat-main
│   ├── chat-header
│   ├── msg-area         (消息列表 — 标题从这里提取)
│   └── ChatInput
└── ChatOutline.vue      (右侧面板 — 新增)
    ├── OutlineSearch.vue
    └── OutlineTree.vue
        └── OutlineGroup  (按消息分组)
            └── OutlineItem (单个标题节点)
```

### 新增文件

```
web/src/components/chat/
├── ChatOutline.vue           # 右侧面板容器
├── OutlineSearch.vue         # 搜索输入框
├── OutlineTree.vue           # 标题树（分组 + 递归渲染）
└── (composables 不单独建目录，放到现有 composables/)
web/src/composables/
├── useOutline.ts             # 标题提取、树构建、搜索、折叠、去抖
└── useActiveHeading.ts       # IntersectionObserver 高亮
```

### 数据结构

```ts
interface Heading {
  id: string          // 注入的 DOM id，如 "heading-msg3-功能特性"
  text: string        // 标题文本
  level: number       // 1-6
  msgId: string       // 所属消息 id
  children: Heading[] // 子标题
}

interface OutlineGroup {
  msgId: string
  msgSummary: string   // 消息摘要（截取前 60 字符）
  msgIndex: number     // 消息序号（如 "AI 回复 #3"）
  headings: Heading[]  // 该消息下的顶级标题树
}
```

### 数据流

```
SSE token 到达
  → MsgRow renderMd() 渲染 HTML (v-html)
  → DOM 更新
  → useOutline watch(messages) 触发 (debounce 300ms)
  → querySelectorAll('.md-body h1, .md-body h2, ...') 提取标题
  → 注入 id 到缺失的标题元素
  → 按 msgId 分组构建 OutlineGroup[]
  → ChatOutline 渲染
  → useActiveHeading 创建 IntersectionObserver
  → 滚动时自动更新 activeId
```

### 标题 id 注入策略

`markdown-it` 默认不在标题上生成 id。需要在渲染后或 DOM 解析时注入：

```ts
// useOutline.ts 中
function ensureHeadingId(el: HTMLElement, msgId: string, index: number): string {
  if (el.id) return el.id
  const id = `h-${msgId}-${index}`
  el.id = id
  return id
}
```

### Canvas 面板互斥逻辑

在 `chat/index.vue` 中新增状态：

```ts
const rightPanel = ref<'outline' | 'canvas' | null>('outline') // 默认显示 outline
```

当 Agent 调用 canvas 工具时：
- `hasCanvasChanges = true` → `rightPanel = 'canvas'`
- 用户可点击切换按钮在 outline/canvas 间切换
- 点击 ✕ 关闭面板 → `rightPanel = null`

## 交互细节

### 搜索

- 输入框 placeholder: "搜索标题…"
- 实时过滤（无防抖，输入即搜）
- 匹配的标题高亮显示匹配文本
- 无匹配时显示 "未找到匹配的标题"

### 键盘

| 键 | 行为 |
|----|------|
| ↑ | 焦点上移一个标题 |
| ↓ | 焦点下移一个标题 |
| Enter | 跳转到焦点标题 |
| Esc | 清除搜索 / 关闭面板 |

### 空状态

```
┌─────────────────────┐
│ 🔍 搜索标题…        │
├─────────────────────┤
│                     │
│   📑 暂无标题        │
│                     │
│   AI 回复中的标题    │
│   将在这里显示       │
│                     │
└─────────────────────┘
```

### 有标题时

```
┌─────────────────────┐
│ 🔍 搜索标题…        │
├─────────────────────┤
│ AI 回复 #1          │
│ ├── 📑 项目概述      │
│ │   ├── 功能特性     │
│ │   └── 技术栈      │
│ ├── 快速开始         │
│ └── API 设计         │
│                     │
│ AI 回复 #3          │
│ ├── 数据库设计       │
│ └── 部署方案         │
└─────────────────────┘
```

## 样式规范

- 面板宽度：260px（比 Canvas 面板的 320px 稍窄）
- 面板背景：跟随主题 `var(--color-surface)`
- 高亮当前标题：左侧 2px 紫色竖线 + 浅紫背景
- 标题缩进：每级 16px
- 字体大小：13px（标题）/ 11px（分组头）
- 滚动条：同 `.msg-area` 的透明 hover 显示策略

## 验收标准

- [ ] 自动解析消息中所有 H1~H6 标题
- [ ] 按消息分组显示标题树
- [ ] 点击标题平滑滚动到对应位置
- [ ] 滚动页面时当前标题自动高亮
- [ ] 搜索框实时过滤标题
- [ ] AI 流式输出时标题树不抖动（300ms 防抖）
- [ ] 深色/浅色模式正确切换
- [ ] 无标题时显示空状态
- [ ] 键盘 ↑↓Enter Esc 正常工作
- [ ] 移动端 Drawer 模式正常
- [ ] 与 Canvas 预览面板互斥切换
- [ ] 不影响现有消息渲染性能
- [ ] 标题 id 注入后不破坏已有样式
