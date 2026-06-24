# ChatInput 表情功能 — 设计文档

**日期**: 2026-06-24
**状态**: 已批准

---

## 目标

在 `ChatInput.vue` 组件的输入工具栏中增加表情按钮，点击弹出完整表情选择器（emoji-mart），选择后插入到 textarea 光标位置。

## 方案

使用 `@emoji-mart/vue`（Vue 3 官方支持）作为表情选择器，通过 Ant Design Vue 的 `a-popover` 承载，依附于工具栏新增的 `SmileOutlined` 按钮。

### 依赖

```json
{
  "@emoji-mart/vue": "latest",
  "@emoji-mart/data": "latest"
}
```

## 架构

```
ChatInput.vue
├── input-actions (现有工具栏)
│   ├── [图片上传]  PaperClipOutlined
│   ├── [文档上传]  FileTextOutlined
│   ├── [表情]      SmileOutlined  ← 新增
│   └── [发送/停止]  SendOutlined / CloseOutlined
│
└── a-popover (新增)
    └── EmojiPicker (@emoji-mart/vue)
```

## 数据流

```
点击表情按钮 → Popover 显示 EmojiPicker
  → 用户选中 emoji
    → 触发 @select 事件 (返回 { native: "😀" })
      → 在 textarea 当前光标位置插入 emoji 字符
      → 关闭 Popover
```

## 涉及文件

| 文件 | 改动 |
|------|------|
| `web/package.json` | 新增 `@emoji-mart/vue` + `@emoji-mart/data` |
| `web/src/components/chat/ChatInput.vue` | 模板: 新增表情按钮 + Popover；脚本: 导入并处理插入逻辑 |

## 关键实现细节

### 光标插入

使用 `textarea.selectionStart` / `selectionEnd` 获取光标位置，在光标处插入 emoji（非末尾追加），插入后恢复焦点。

```ts
function insertEmoji(emoji: string) {
  const el = textareaRef.value
  if (!el) return
  const start = el.selectionStart
  const end = el.selectionEnd
  const before = inputText.value.slice(0, start)
  const after = inputText.value.slice(end)
  inputText.value = before + emoji + after
  // 恢复光标位置
  nextTick(() => {
    el.focus()
    el.selectionStart = el.selectionEnd = start + emoji.length
  })
}
```

### Popover 定位

- `placement="top"`，表情面板浮在输入框上方
- `trigger="click"`，点击按钮打开/关闭
- `:visible` 受控，选择 emoji 后关闭

### 状态

- `loading` 时表情按钮 disabled（与现有工具按钮行为一致）
- 选择 emoji 后 Popover 自动关闭

### Vue 模板规范

遵循项目规范：`v-if` / `v-for` 必须在 `<template>` 标签上。

## 不包含

- 自定义 emoji 集合（使用 emoji-mart 默认集）
- emoji 常用记录/频率排序（emoji-mart 内置支持，后续可开启）
- 皮肤色调选择（emoji-mart 默认支持）
