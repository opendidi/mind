<template>
  <template v-if="collapsed">
    <!-- Collapsed: FAB to reopen -->
    <div class="agent-fab" @click="collapsed = false" title="打开 AI 助手 (Ctrl+Shift+A)">
      <span class="agent-fab-icon">🤖</span>
    </div>
  </template>
  <template v-else>
    <div class="agent-panel" :style="{ width: panelWidth + 'px' }">
      <!-- Header -->
      <div class="agent-panel-header">
        <span class="agent-panel-title">AI 助手</span>
        <div class="agent-panel-header-actions">
          <template v-if="canvasStatus">
            <span class="canvas-status-tag">{{ canvasStatus }}</span>
          </template>
          <a-button size="small" type="text" @click="stream.clear()" title="清空对话">
            <DeleteOutlined />
          </a-button>
          <a-button size="small" type="text" @click="collapsed = true" title="收起面板">
            <RightOutlined />
          </a-button>
        </div>
      </div>

      <!-- Error banner -->
      <template v-if="stream.state.error">
        <div class="agent-error">
          <span>{{ stream.state.error }}</span>
          <a-button size="small" type="link" @click="stream.state.error = null"> ✕ </a-button>
        </div>
      </template>

      <!-- Canvas context hint -->
      <template v-if="selectionHint">
        <div class="agent-selection-hint">
          <span class="hint-icon">🎯</span>
          <span>{{ selectionHint }}</span>
          <a-button size="small" type="link" @click="clearSelectionHint">清除</a-button>
        </div>
      </template>

      <!-- Messages -->
      <div ref="msgListRef" class="agent-messages">
        <template v-for="msg in stream.state.messages" :key="msg.id">
          <AgentMessageItem :message="msg" @locate-pens="onLocatePens" />
        </template>

        <template v-if="stream.state.loading">
          <div class="agent-typing">
            <span class="typing-dot"></span>
            <span class="typing-dot"></span>
            <span class="typing-dot"></span>
          </div>
        </template>
      </div>

      <!-- Input -->
      <div class="agent-input-wrap">
        <AgentInput
          :disabled="stream.state.loading"
          :initial-value="presetInput"
          :canvas-hint="canvasHint"
          @send="handleSend"
        />
      </div>

      <!-- Resize handle -->
      <div class="agent-resize-handle" @mousedown="onResizeStart"></div>
    </div>
  </template>
</template>

<script setup lang="ts">
import { ref, watch, nextTick, onMounted, onUnmounted, computed } from 'vue'
import { DeleteOutlined, RightOutlined } from '@ant-design/icons-vue'
import { AgentStreamHandler } from './AgentStreamHandler'
import AgentMessageItem from './AgentMessageItem.vue'
import AgentInput from './AgentInput.vue'
import { executeCanvasTool } from '@/utils/canvasBridge'
import { useSelection } from '@/services/selections'

const collapsed = ref(true)
const panelWidth = ref(420)
const msgListRef = ref<HTMLElement>()
const stream = new AgentStreamHandler()

// ── Canvas tracking ──────────────────────────────────────
const canvasPenCount = ref(0)
const selectionHint = ref('')

const canvasHint = computed(() => {
  if (selectionHint.value) return selectionHint.value
  if (canvasPenCount.value > 0) return `画布有 ${canvasPenCount.value} 个节点`
  return ''
})

const canvasStatus = computed(() => {
  if (stream.state.loading) return null
  if (canvasPenCount.value > 0) return `${canvasPenCount.value} 个节点`
  return null
})

function updateCanvasPenCount() {
  try {
    const meta2d = (window as any).meta2d
    if (meta2d) {
      const data = meta2d.data()
      canvasPenCount.value = data?.pens?.length || 0
    }
  } catch {
    console.warn('[AgentPanel] not on editor page — Meta2D unavailable for pen count')
  }
}

// Wire tool results to Meta2D canvas operations
stream.onToolResult(async (tool, args, success, result) => {
  console.log('[AgentPanel] onToolResult:', { tool, args, success })
  try {
    const handled = await executeCanvasTool(tool, args, success, result)
    if (handled) {
      console.log('[AgentPanel] canvas tool executed OK, updating state')
      stream.markCanvasChanged()
      updateCanvasPenCount()
    } else {
      console.warn('[AgentPanel] canvas tool failed:', { tool, args })
    }
  } catch (err) {
    console.warn('[AgentPanel] executeCanvasTool error:', err)
  }
})

// ── Selection injection ──────────────────────────────────
let presetInput = ''
const { selections } = useSelection()

/** Build a rich context description for a single selected pen. */
function buildPenContext(pen: any): string {
  const parts: string[] = [
    `ID=${pen.id}`,
    `类型=${pen.name || 'unknown'}`,
  ]
  if (pen.text) parts.push(`文字="${pen.text.slice(0, 100)}"`)
  parts.push(
    `位置=(${pen.x}, ${pen.y})`,
    `大小=${pen.width}x${pen.height}`,
    `背景色=${pen.background || '默认'}`,
    `文字色=${pen.color || '默认'}`,
  )
  if (pen.fontFamily) parts.push(`字体=${pen.fontFamily} ${pen.fontSize || 14}px`)
  if (pen.fontWeight && pen.fontWeight !== 'normal') parts.push(`粗细=${pen.fontWeight}`)
  if (pen.textAlign && pen.textAlign !== 'center') parts.push(`对齐=${pen.textAlign}`)
  if (pen.borderRadius) parts.push(`圆角=${pen.borderRadius}px`)
  if (pen.borderColor) parts.push(`边框色=${pen.borderColor}`)
  if (pen.lineDash?.length) parts.push(`虚线=${pen.lineDash.join(',')}`)
  if (pen.shadowColor) parts.push('阴影=有')
  if (pen.gradientColors) parts.push('渐变=有')
  if (pen.icon) parts.push(`图标=${pen.icon}`)
  if (pen.image) parts.push('图片=有')
  if (pen.locked) parts.push('【已锁定】')
  if (pen.tags?.length) parts.push(`标签=${pen.tags.join(', ')}`)
  return parts.join('，')
}

watch(
  () => selections.pen,
  pen => {
    if (collapsed.value || !pen) {
      selectionHint.value = ''
      presetInput = ''
      return
    }
    const name = pen.name || '节点'
    const text = (pen.text || '').slice(0, 30)
    const id = (pen as any).id || ''
    selectionHint.value = `选中: ${name} "${text}" [ID: ${id}]`
  },
)

watch(
  () => (window as any).meta2d?.active,
  activePens => {
    if (!activePens || activePens.length < 2) return
    const ids = activePens.map((p: any) => p.id || p.penId).filter(Boolean).join(', ')
    selectionHint.value = `选中 ${activePens.length} 个节点 [IDs: ${ids}]`
  },
)

function clearSelectionHint() {
  selectionHint.value = ''
  presetInput = ''
}

// ── Locate pens (from tool card click) ───────────────────
function onLocatePens(penIds: string[]) {
  const meta2d = (window as any).meta2d
  if (!meta2d || !penIds.length) return
  const pens = penIds.map(id => meta2d.findOne(id)).filter(Boolean)
  if (pens.length) {
    meta2d.fitView(pens, 24)
  }
}

// ── Resize ───────────────────────────────────────────────
let resizeDragging = false
function onResizeStart(e: MouseEvent) {
  resizeDragging = true
  const startX = e.clientX
  const startW = panelWidth.value
  const onMove = (ev: MouseEvent) => {
    const w = startW + (startX - ev.clientX)
    panelWidth.value = Math.max(320, Math.min(600, w))
  }
  const onUp = () => {
    resizeDragging = false
    document.removeEventListener('mousemove', onMove)
    document.removeEventListener('mouseup', onUp)
    document.body.style.cursor = ''
    document.body.style.userSelect = ''
  }
  document.addEventListener('mousemove', onMove)
  document.addEventListener('mouseup', onUp)
  document.body.style.cursor = 'ew-resize'
  document.body.style.userSelect = 'none'
}

// ── Keyboard shortcut ────────────────────────────────────
function onKeydown(e: KeyboardEvent) {
  if (e.ctrlKey && e.shiftKey && e.key === 'A') {
    e.preventDefault()
    collapsed.value = !collapsed.value
  }
}

// ── Lifecycle ────────────────────────────────────────────
function handleSend(text: string, images?: string[]) {
  // Attach selection context if present
  let fullText = text
  const selHint = selectionHint.value
  if (selHint) {
    fullText = `[画布上下文] ${selHint}\n${text}`
    clearSelectionHint()
  }
  // If presetInput was used (e.g. auto-generated pen context), clear it after send
  if (presetInput && text.includes(presetInput.slice(0, 30))) {
    presetInput = ''
  }
  stream.send(fullText, images)
}

// Auto-scroll to bottom
watch(
  () => [stream.state.messages.length, stream.state.toolCalls.length],
  () => {
    nextTick(() => {
      if (msgListRef.value) {
        msgListRef.value.scrollTop = msgListRef.value.scrollHeight
      }
    })
  },
)

onMounted(() => {
  document.addEventListener('keydown', onKeydown)
  updateCanvasPenCount()
  // Monitor canvas mutations from user editing
  window.addEventListener('meta2d:agent-mutation', updateCanvasPenCount)
})

onUnmounted(() => {
  stream.abort()
  document.removeEventListener('keydown', onKeydown)
  window.removeEventListener('meta2d:agent-mutation', updateCanvasPenCount)
})

function setContext(text: string) {
  presetInput = text
  selectionHint.value = ''
}

defineExpose({ collapsed, setContext })
</script>

<style scoped lang="less">
.agent-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #fafafa;
  border-left: 1px solid #e8e8e8;
  position: relative;
  flex-shrink: 0;
}

.agent-panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 12px;
  height: 40px;
  border-bottom: 1px solid #e8e8e8;
  background: #fff;
  flex-shrink: 0;

  .agent-panel-title {
    font-size: 14px;
    font-weight: 600;
    color: #1e293b;
  }

  .agent-panel-header-actions {
    display: flex;
    align-items: center;
    gap: 4px;
  }
}

.canvas-status-tag {
  font-size: 11px;
  padding: 1px 8px;
  border-radius: 10px;
  background: #eef2ff;
  color: #4f46e5;
  font-weight: 500;
}

.agent-selection-hint {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  background: #fef3c7;
  border-bottom: 1px solid #fcd34d;
  font-size: 12px;
  color: #92400e;
  flex-shrink: 0;

  .hint-icon {
    font-size: 14px;
  }
}

.agent-error {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 16px;
  background: #fff2f0;
  border-bottom: 1px solid #ffccc7;
  color: #ff4d4f;
  font-size: 13px;
  flex-shrink: 0;
}

.agent-messages {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.agent-typing {
  display: flex;
  gap: 4px;
  padding: 12px 16px;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
  align-self: flex-start;

  .typing-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #bbb;
    animation: typing-bounce 1.4s infinite both;

    &:nth-child(2) {
      animation-delay: 0.2s;
    }

    &:nth-child(3) {
      animation-delay: 0.4s;
    }
  }
}

@keyframes typing-bounce {
  0%,
  60%,
  100% {
    transform: translateY(0);
  }
  30% {
    transform: translateY(-4px);
  }
}

.agent-input-wrap {
  border-top: 1px solid #e8e8e8;
  padding: 12px 16px;
  background: #fff;
  flex-shrink: 0;
}

.agent-resize-handle {
  position: absolute;
  left: -3px;
  top: 0;
  bottom: 0;
  width: 6px;
  cursor: ew-resize;
  z-index: 10;
  transition: background 0.15s;

  &:hover {
    background: rgba(#4f46e5, 0.15);
  }
}

// Collapsed FAB
.agent-fab {
  position: fixed;
  right: 16px;
  bottom: 80px;
  width: 44px;
  height: 44px;
  border-radius: 50%;
  background: linear-gradient(135deg, #818cf8, #c084fc);
  box-shadow: 0 4px 16px rgba(129, 140, 248, 0.35);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  z-index: 100;
  transition:
    transform 0.15s,
    box-shadow 0.15s;

  &:hover {
    transform: scale(1.1);
    box-shadow: 0 6px 20px rgba(129, 140, 248, 0.45);
  }

  .agent-fab-icon {
    font-size: 20px;
    line-height: 1;
  }
}
</style>
