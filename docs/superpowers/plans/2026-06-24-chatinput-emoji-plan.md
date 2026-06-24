# ChatInput 表情功能 — 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 ChatInput 的输入工具栏中新增表情按钮，弹出 emoji-mart 完整表情选择器，选择后插入到 textarea 光标位置。

**Architecture:** 安装 `@emoji-mart/vue` + `@emoji-mart/data`，在 `ChatInput.vue` 的 `.input-actions` 区域新增 `SmileOutlined` 按钮，使用 `<a-popover>` 承载 EmojiPicker 组件。选择 emoji 时，通过 textarea 的 `selectionStart`/`selectionEnd` 在光标处插入，`nextTick` 后恢复焦点和光标位置。

**Tech Stack:** Vue 3 + TypeScript, @emoji-mart/vue, @emoji-mart/data, Ant Design Vue 3.2.20

---

### Task 1: Install emoji-mart 依赖

**Files:**
- Modify: `web/package.json`

- [ ] **Step 1: 安装 @emoji-mart/vue 和 @emoji-mart/data**

```bash
cd web && pnpm add @emoji-mart/vue @emoji-mart/data
```

Expected: 两个包添加到 `dependencies`，`pnpm-lock.yaml` 更新。

- [ ] **Step 2: 验证安装**

```bash
cd web && node -e "require('@emoji-mart/vue'); console.log('OK')"
```

Expected: 无错误输出 `OK`（包存在且可解析）。注意：如果 @emoji-mart/vue 是 ESM-only，此检查可能报错，跳过即可——以 pnpm add 成功为准。

- [ ] **Step 3: Commit**

```bash
git add web/package.json web/pnpm-lock.yaml
git commit -m "chore: add @emoji-mart/vue and @emoji-mart/data for emoji picker"
```

---

### Task 2: ChatInput.vue — Script 改动（导入、状态、插入逻辑）

**Files:**
- Modify: `web/src/components/chat/ChatInput.vue` (script 区域)

- [ ] **Step 1: 增加 import**

在 `<script setup>` 顶部现有 import 块中添加：

```ts
import { ref, computed, nextTick } from 'vue'  // nextTick 从 vue 解构中新增
import { CloseOutlined, SendOutlined, PaperClipOutlined, FileTextOutlined, SmileOutlined } from '@ant-design/icons-vue'
import data from '@emoji-mart/data'
import Picker from '@emoji-mart/vue'
```

具体修改（当前第 99-101 行）：
- 第 99 行：`import { ref, computed } from 'vue'` → `import { ref, computed, nextTick } from 'vue'`
- 第 100 行：`import { CloseOutlined, SendOutlined, PaperClipOutlined, FileTextOutlined } from '@ant-design/icons-vue'` → 末尾追加 `, SmileOutlined`
- 第 101 行之后新增两行导入。

- [ ] **Step 2: 新增表情相关响应式状态**

在 `docAttachments` 定义之后（当前第 136 行之后）添加：

```ts
// Emoji picker
const showEmoji = ref(false)
```

- [ ] **Step 3: 新增 insertEmoji 函数**

在 `onTextareaInput` 函数之后（当前第 188 行之后）添加：

```ts
function onEmojiSelect(emoji: { native: string }) {
  const el = textareaRef.value
  if (!el) return
  const start = el.selectionStart
  const end = el.selectionEnd
  const before = inputText.value.slice(0, start)
  const after = inputText.value.slice(end)
  inputText.value = before + emoji.native + after
  showEmoji.value = false
  nextTick(() => {
    el.focus()
    const pos = start + emoji.native.length
    el.selectionStart = pos
    el.selectionEnd = pos
  })
}
```

- [ ] **Step 4: Commit**

```bash
git add web/src/components/chat/ChatInput.vue
git commit -m "feat: add emoji picker imports and insert logic to ChatInput"
```

---

### Task 3: ChatInput.vue — Template 改动（表情按钮 + Popover）

**Files:**
- Modify: `web/src/components/chat/ChatInput.vue` (template 区域)

- [ ] **Step 1: 在工具栏中新增表情按钮**

在文档上传按钮之后、发送/终止按钮之前（第 81-82 行之间）插入表情按钮：

```html
        <!-- Emoji picker button -->
        <a-popover
          v-model:open="showEmoji"
          trigger="click"
          placement="top"
          :overlayStyle="{ padding: 0 }"
        >
          <template #content>
            <Picker :data="data" :locale="'zh'" @select="onEmojiSelect" />
          </template>
          <a-tooltip title="表情">
            <a-button type="text" class="tool-btn" :disabled="loading" @click="showEmoji = !showEmoji">
              <SmileOutlined />
            </a-button>
          </a-tooltip>
        </a-popover>
```

- [ ] **Step 2: Commit**

```bash
git add web/src/components/chat/ChatInput.vue
git commit -m "feat: add emoji button and popover to ChatInput template"
```

---

### Task 4: 验证

**Files:**
- 无需修改

- [ ] **Step 1: 启动开发服务器验证**

```bash
cd web && pnpm start
```

Expected: 
1. 开发服务器启动无编译错误
2. 在输入框工具栏看到表情按钮（笑脸图标）
3. 点击表情按钮，弹出 emoji 选择器面板
4. 点击任意 emoji，字符插入到 textarea 光标位置
5. 选择后面板自动关闭
6. `loading` 状态（AI 回复中）时表情按钮为 disabled
7. `.vue` 文件无 TypeScript 报错

- [ ] **Step 2: 类型检查**

```bash
cd web && npx vue-tsc --noEmit
```

Expected: 无新增类型错误。

- [ ] **Step 3: 最终 Commit（如有微调）**

如果验证中发现问题并修复，提交修改。
