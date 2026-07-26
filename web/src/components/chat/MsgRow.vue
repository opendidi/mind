<!-- Message row — user / agent / tool / error -->
<template>
  <!-- User message -->
  <template v-if="message.role === 'user'">
    <div :data-msg-id="message.id" class="msg-row user" :class="{ selectable: selectable }">
      <template v-if="selectable">
        <a-checkbox class="msg-check" :checked="selected" @change="$emit('toggleSelect', message.id)" />
      </template>
      <div class="msg-avatar user">U</div>
      <MsgContextMenu
        show-translate
        @copy="emit('copy', message.text || '')"
        @translate="tl.showPopover"
        @quote="emit('quoteMsg', message.id)"
        @delete="emit('delete', message.id)"
      >
        <div class="msg-content" @contextmenu="onContextMenu">
          <template v-if="message.images && message.images.length > 0">
            <div class="msg-images-row">
              <template v-for="(img, ii) in message.images" :key="ii">
                <div class="msg-image-thumb" @click="previewImage(img)">
                  <img :src="img" alt="图片" />
                </div>
              </template>
            </div>
          </template>
          <template v-if="message.files && message.files.length > 0">
            <div class="msg-files-row">
              <div v-for="(f, i) in message.files" :key="'f-' + i" class="msg-file-chip">
                <FileTextOutlined class="file-icon" />
                <span class="file-name">{{ f.name }}</span>
              </div>
            </div>
          </template>
          <template v-if="message.quote">
            <div class="msg-quote-block">
              <div class="quote-line"></div>
              <div class="quote-body">
                <span class="quote-role">{{ message.quote.role === 'user' ? '你' : 'AI' }}</span>
                {{ message.quote.text }}
              </div>
            </div>
          </template>
          <div v-if="isEditing" class="msg-edit-row">
            <textarea v-model="editText" class="msg-edit-input" @keydown="onEditKeydown" @blur="cancelEdit" />
            <span class="msg-edit-hint">Enter 保存 · Esc 取消</span>
          </div>
          <div v-else class="msg-bubble user" @dblclick="startEdit" :title="selectable ? '' : '双击编辑'">
            {{ message.text }}
          </div>
          <MsgActions
            v-if="!isEditing"
            :selectable="selectable"
            @copy="$emit('copy', message.text || '')"
            @quote="$emit('quote', { text: message.text || '', msgId: message.id, role: 'user' })"
            @start-select="$emit('startSelect', message.id)"
          />
        </div>
      </MsgContextMenu>
    </div>
  </template>

  <!-- AI reply -->
  <template v-else-if="message.role === 'agent'">
    <div :data-msg-id="message.id" class="msg-row assistant" :class="{ selectable: selectable }">
      <template v-if="selectable">
        <a-checkbox class="msg-check" :checked="selected" @change="$emit('toggleSelect', message.id)" />
      </template>
      <div class="msg-avatar ai">
        <i class="icon-ds block ds-small"></i>
      </div>
      <MsgContextMenu
        show-translate
        @copy="emit('copy', message.text || '')"
        @translate="tl.showPopover"
        @quote="emit('quoteMsg', message.id)"
        @delete="emit('delete', message.id)"
      >
        <div class="msg-content" @contextmenu="onContextMenu">
          <!-- Phase 1: Deep thinking / reasoning (DeepSeek-R1 style) -->
          <ThinkCard
            v-if="message.thinking"
            :content="message.thinking"
            :thinking="message.thinkingActive === true"
            :duration="message.thinkingDuration"
          />
          <!-- Phase 2: Search results / citations -->
          <MsgReferenceCard
            :references="message.references"
            :search-type="message.refsSearchType"
            @selectRefs="refs => $emit('selectRefs', refs)"
          />
          <!-- Phase 3: Final answer with inline citations -->
          <div class="msg-bubble assistant mt-2" :class="{ 'is-streaming': streaming }">
            <template v-for="(seg, si) in messageSegments" :key="si">
              <template v-if="seg.type === 'text' && seg.content.trim()">
                <div class="md-body" v-html="renderSegMd(seg.content)" />
              </template>
              <template v-else-if="seg.type === 'files'">
                <FileCard :files="seg.data" />
              </template>
              <template v-else-if="seg.type === 'mindmap'">
                <MindMapCard :markdown="seg.content" />
              </template>
              <template v-else-if="seg.type === 'map'">
                <MapCard
                  :title="seg.data.title"
                  :center="seg.data.center"
                  :zoom="seg.data.zoom"
                  :markers="seg.data.markers"
                />
              </template>
              <template v-else-if="seg.type === 'route'">
                <RouteCard :mode="seg.data.mode" :from="seg.data.from" :to="seg.data.to" />
              </template>
              <template v-else-if="seg.type === 'code'">
                <div class="code-block">
                  <div class="code-header">
                    <span class="code-lang">{{ seg.language || 'text' }}</span>
                    <span class="code-copy-btn" @click.stop="onCopyCode(seg.content || '', si)">
                      <CopyOutlined />
                      <span>{{ codeCopiedId === `code-${si}` ? '已复制' : '复制代码' }}</span>
                    </span>
                  </div>
                  <pre class="code-body">
                    <code>{{ seg.content }}</code>
                  </pre>
                </div>
              </template>
            </template>
          </div>
          <MsgActions
            flip-quote
            show-feedback
            :feedback-class="fbClass"
            :show-tts="ttsSupported"
            :tts-speaking="ttsSpeaking"
            :selectable="selectable"
            @copy="$emit('copy', message.text || '')"
            @quote="$emit('quote', { text: message.text || '', msgId: message.id, role: 'agent' })"
            @feedback="onFeedBack"
            @toggle-speak="onToggleSpeak"
            @start-select="$emit('startSelect', message.id)"
          />
        </div>
      </MsgContextMenu>
    </div>
  </template>

  <!-- Tool call -->
  <template v-else-if="message.role === 'tool' && message.tool">
    <div :data-msg-id="message.id" class="msg-row tool-row" :class="{ selectable: selectable }">
      <template v-if="selectable">
        <a-checkbox class="msg-check" :checked="selected" @change="$emit('toggleSelect', message.id)" />
      </template>
      <div class="msg-content">
        <div
          class="tool-card"
          :class="{
            'tool-ok': message.tool.success === true,
            'tool-fail': message.tool.success === false,
            expanded: toolExpanded,
          }"
        >
          <div class="tool-header" @click="onToggleTool">
            <span class="tool-name">{{ message.tool.name }}</span>
            <template v-if="message.tool.success === undefined">
              <span class="tool-status pending">执行中</span>
            </template>
            <template v-else-if="message.tool.success">
              <span class="tool-status ok">完成</span>
            </template>
            <template v-else>
              <span class="tool-status fail">失败</span>
            </template>
            <template v-if="message.tool.result !== undefined">
              <svg
                class="tool-chevron"
                :class="{ rotated: toolExpanded }"
                viewBox="0 0 24 24"
                width="12"
                height="12"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
              >
                <path d="M6 9l6 6 6-6" />
              </svg>
            </template>
          </div>
          <template v-if="toolExpanded && message.tool.result !== undefined">
            <div class="tool-body">
              <pre class="tool-result" :class="{ fail: message.tool.success === false }">{{ formattedToolResult }}</pre>
            </div>
          </template>
        </div>
        <template v-if="toolCanvasData">
          <CanvasPreview :nodes="toolCanvasData.nodes" :edges="toolCanvasData.edges" />
        </template>
        <template v-if="toolFileData">
          <FileCard :files="toolFileData" />
        </template>
      </div>
    </div>
  </template>

  <!-- Error -->
  <template v-else-if="message.role === 'error'">
    <div :data-msg-id="message.id" class="msg-row assistant" :class="{ selectable: selectable }">
      <template v-if="selectable">
        <a-checkbox class="msg-check" :checked="selected" @change="$emit('toggleSelect', message.id)" />
      </template>
      <div class="msg-avatar ai">!</div>
      <div class="msg-content">
        <div class="msg-bubble error">{{ message.text }}</div>
        <span class="msg-retry" title="重试" @click="$emit('retry')"><ReloadOutlined /> 重试</span>
      </div>
    </div>
  </template>

  <ImageViewer :src="previewSrc" @close="previewSrc = ''" />

  <SelectionToolbar
    :x="quotePos.x"
    :y="quotePos.y"
    :visible="quoteVisible"
    :tts-supported="ttsSupported"
    @copy="onCopySelection"
    @quote="onQuoteSelection"
    @translate="onTranslateSelection"
    @speak="onSpeakSelection"
  />

  <template v-if="tl.pos.value">
    <TranslatePopover
      :x="tl.pos.value.x"
      :y="tl.pos.value.y"
      :loading="tl.loading.value"
      :error="tl.error.value"
      :translated="tl.result.value"
      :engine="tl.engine.value"
      :source-lang="tl.srcLang.value"
      :target-lang="tl.tgtLang.value"
      :style="tl.style.value"
      @close="tl.close"
      @change-target="tl.changeTarget"
      @change-style="tl.changeStyle"
    />
  </template>
</template>

<script setup lang="ts">
// @ts-nocheck — Meta2D type definitions are too complex for strict TS checking
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import { CopyOutlined, ReloadOutlined, FileTextOutlined } from '@ant-design/icons-vue'
import type { ChatMessage } from '@/composables/useAgentChat'
import { useSpeech } from '@/composables/useSpeech'
import FileCard from './FileCard.vue'
import MindMapCard from './MindMapCard.vue'
import MapCard from '@/components/shared/MapCard.vue'
import RouteCard from '@/components/shared/RouteCard.vue'
import CanvasPreview from './CanvasPreview.vue'
import TranslatePopover from './TranslatePopover.vue'
import ThinkCard from './ThinkCard.vue'
import { useTranslate } from '@/composables/useTranslate'
import { parseMessageSegments } from '@/utils/messageSegments'
import type { MsgSegment } from '@/utils/messageSegments'
import MsgContextMenu from './MsgContextMenu.vue'
import MsgReferenceCard from './MsgReferenceCard.vue'
import SelectionToolbar from './SelectionToolbar.vue'
import ImageViewer from './ImageViewer.vue'
import MsgActions from './MsgActions.vue'

const props = defineProps<{
  message: ChatMessage
  renderMd: (text: string) => string
  selectable?: boolean
  selected?: boolean
  streaming?: boolean
}>()

const emit = defineEmits<{
  copy: [text: string]
  toggleSelect: [msgId: string]
  startSelect: [msgId: string]
  feedback: [msgId: string, type: string]
  quote: [data: { text: string; msgId: string; role: string }]
  quoteMsg: [msgId: string]
  retry: []
  delete: [msgId: string]
  edit: [msgId: string, newText: string]
  selectRefs: [refs: Array<{ title?: string; url: string; snippet?: string; domain?: string }>]
}>()

const toolExpanded = ref(false)
const fbState = ref(props.message.feedback || '')

// ── Message editing ──────────────────────────────────────────
const isEditing = ref(false)
const editText = ref('')
let editTextareaRef: HTMLTextAreaElement | null = null

function startEdit() {
  if (props.message.role !== 'user') return
  editText.value = props.message.text || ''
  isEditing.value = true
  // Focus after Vue renders the textarea
  requestAnimationFrame(() => {
    editTextareaRef?.focus()
    editTextareaRef?.select()
  })
}

function confirmEdit() {
  const newText = editText.value.trim()
  if (newText && newText !== props.message.text) {
    emit('edit', props.message.id, newText)
  }
  cancelEdit()
}

function cancelEdit() {
  isEditing.value = false
  editText.value = ''
}

function onEditKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    confirmEdit()
  } else if (e.key === 'Escape') {
    cancelEdit()
  }
}

const fbClass = computed(() => ({
  liked: fbState.value === 'liked',
  disliked: fbState.value === 'disliked',
}))

watch(
  () => props.message.feedback,
  val => {
    fbState.value = val || ''
  },
)

function onToggleTool() {
  if (props.message.tool?.result !== undefined) {
    toolExpanded.value = !toolExpanded.value
  }
}

const formattedToolResult = computed(() => {
  const result = props.message.tool?.result
  if (result === undefined) return ''
  if (typeof result === 'string') return result
  try {
    return JSON.stringify(result, null, 2)
  } catch {
    return String(result)
  }
})

const toolCanvasData = computed(() => {
  const result = props.message.tool?.result
  if (!result || typeof result !== 'object') return null
  const r = result as Record<string, unknown>
  const data = (r.data || r) as Record<string, unknown>
  const diagram = data?.diagram as Record<string, unknown> | undefined
  if (diagram?.nodes && Array.isArray(diagram.nodes)) {
    return { nodes: diagram.nodes, edges: (diagram.edges as any[]) || [] }
  }
  return null
})

// Detect file_search results in tool output → auto-render as FileCard
const toolFileData = computed(() => {
  const tool = props.message.tool
  if (!tool || tool.name !== 'file_search') return null
  const result = tool.result
  if (!result || typeof result !== 'object') return null
  const r = result as Record<string, unknown>
  const data = (r.data || r) as Record<string, unknown>
  const items = data?.items as any[] | undefined
  if (!items || !Array.isArray(items) || items.length === 0) return null
  return items
})

// ── Image preview lightbox ────────────────────────────────

const previewSrc = ref('')

function previewImage(src: string) {
  previewSrc.value = src
}

function onFeedBack(type: string) {
  fbState.value = fbState.value === type ? '' : type
  emit('feedback', props.message.id, fbState.value)
}

const messageSegments = computed(() => parseMessageSegments(props.message.text || ''))

// ── Code block copy ─────────────────────────────────────────

const codeCopiedId = ref('')

function onCopyCode(code: string, si: number) {
  emit('copy', code)
  const id = `code-${si}`
  codeCopiedId.value = id
  setTimeout(() => {
    if (codeCopiedId.value === id) codeCopiedId.value = ''
  }, 2000)
}

function renderSegMd(text: string): string {
  if (!text.trim()) return ''
  const html = props.renderMd(text)
  return styleCitations(html)
}

/** Wrap [N] citation markers in styled superscript, skipping code blocks. */
function styleCitations(html: string): string {
  const parts = html.split(/(<pre[\s\S]*?<\/pre>|<code[\s\S]*?<\/code>)/g)
  return parts
    .map((part, i) => {
      if (i % 2 === 1) return part
      return part.replace(/\[(\d+)\]/g, '<sup class="cite-num">[$1]</sup>')
    })
    .join('')
}

// ── TTS ──

const { speaking: ttsSpeaking, supported: ttsSupported, speak, stop } = useSpeech()

function onToggleSpeak() {
  if (ttsSpeaking.value) {
    stop()
  } else {
    speak(props.message.text || '')
  }
}

// ── Text selection floating toolbar ──

const quoteVisible = ref(false)
const quotePos = ref({ x: 0, y: 0 })

function onContextMenu(e: MouseEvent) {
  const sel = window.getSelection()?.toString().trim()
  if (!sel) return
  e.preventDefault()
  e.stopPropagation()
  quotePos.value = { x: e.clientX + 8, y: e.clientY + 4 }
  quoteVisible.value = true
}

function hideContextMenu() {
  quoteVisible.value = false
}

function onCopySelection() {
  const text = window.getSelection()?.toString().trim()
  const fallback = props.message.text || ''
  emit('copy', text || fallback)
  quoteVisible.value = false
}

function onQuoteSelection() {
  const text = window.getSelection()?.toString().trim()
  const fallback = props.message.text || ''
  emit('quote', {
    text: text || fallback,
    msgId: props.message.id,
    role: props.message.role,
  })
  quoteVisible.value = false
}

function onSpeakSelection() {
  const text = window.getSelection()?.toString().trim()
  if (text) speak(text)
  quoteVisible.value = false
}

function onTranslateSelection() {
  quoteVisible.value = false
  tl.showPopover()
}

// ── Translation ───────────────────────────────────────────
const tl = useTranslate(props.message.text || '', props.message.id)

onMounted(() => {
  document.addEventListener('click', hideContextMenu)
})

onBeforeUnmount(() => {
  document.removeEventListener('click', hideContextMenu)
})
</script>

<style lang="scss" scoped>
@use 'sass:color';
@use '@/assets/styles/variables.scss' as *;

.icon-ds {
  display: block;
  background: linear-gradient(135deg, #818cf8, #c084fc);
  clip-path: polygon(50% 0%, 62% 38%, 100% 50%, 62% 62%, 50% 100%, 38% 62%, 0% 50%, 38% 38%);
  width: 28px;
  height: 28px;
  &.ds-small {
    width: 18px;
    height: 18px;
    animation: none;
  }
}

.msg-row {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
  align-items: flex-start;

  &.user {
    flex-direction: row-reverse;
    .msg-content {
      display: flex;
      flex-direction: column;
      align-items: flex-end;
    }
    .msg-bubble,
    .msg-quote-block {
      width: fit-content;
      max-width: 100%;
    }
  }
  &.selectable {
    cursor: pointer;
  }

  .msg-check {
    margin-top: 6px;
    flex-shrink: 0;
  }

  .msg-avatar {
    width: 32px;
    height: 32px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 13px;
    font-weight: 700;
    flex-shrink: 0;
    &.user {
      background: #e0e7ff;
      color: $primary;
    }
    &.ai {
      background: linear-gradient(135deg, $primary, #7c3aed);
      color: #fff;
    }
  }

  .msg-content {
    max-width: 75%;
    min-width: 0;
  }

  .msg-bubble {
    padding: 10px 16px;
    border-radius: 16px;
    font-size: 14px;
    line-height: 1.65;
    &.user {
      background: $primary;
      color: #fff;
      border-bottom-right-radius: 4px;
    }
    &.assistant {
      background: #f1f5f9;
      color: $text;
      border-bottom-left-radius: 4px;
    }
    &.error {
      background: #fef2f2;
      color: #dc2626;
      border: 1px solid #fecaca;
    }
  }

  .msg-retry {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    margin-top: 6px;
    padding: 2px 10px;
    font-size: 12px;
    color: #dc2626;
    cursor: pointer;
    border-radius: 6px;
    background: #fef2f2;
    border: 1px solid #fecaca;
    transition: all 0.15s;
    &:hover {
      background: #fee2e2;
      border-color: #fca5a5;
    }
  }

  &:hover :deep(.msg-copy),
  &:hover :deep(.msg-speak),
  &:hover :deep(.msg-feedback),
  &:hover :deep(.msg-select-trigger),
  &:hover :deep(.msg-quote-btn) {
    opacity: 1;
  }
}

.msg-quote-block {
  display: flex;
  gap: 6px;
  margin-bottom: 6px;
  padding: 6px 10px;
  background: rgba(79, 70, 229, 0.04);
  border-radius: 8px;
  .quote-body {
    flex: 1;
    font-size: 12px;
    color: $text-secondary;
    line-height: 1.5;
  }
  .quote-role {
    display: inline-block;
    padding: 1px 5px;
    margin-right: 4px;
    font-size: 10px;
    font-weight: 600;
    color: $primary;
    background: rgba($primary, 0.1);
    border-radius: 3px;
  }
  .quote-line {
    width: 3px;
    border-radius: 2px;
    background: $primary;
    flex-shrink: 0;
    opacity: 0.5;
    align-self: stretch;
  }
}

.msg-images-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: flex-end;
  margin-bottom: 8px;
  .msg-image-thumb {
    width: 96px;
    height: 96px;
    flex-shrink: 0;
    border-radius: 12px;
    overflow: hidden;
    border: 2px solid rgba($primary, 0.1);
    cursor: pointer;
    transition: transform 0.15s, border-color 0.15s;
    img {
      width: 100%;
      height: 100%;
      object-fit: cover;
      display: block;
    }
    &:hover {
      transform: scale(1.06);
      border-color: $primary;
    }
  }
}

.msg-files-row {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  justify-content: flex-end;
  margin-bottom: 8px;
  .msg-file-chip {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    padding: 5px 10px;
    border-radius: 8px;
    background: rgba(79, 70, 229, 0.06);
    border: 1px solid rgba(79, 70, 229, 0.15);
    .file-icon {
      font-size: 14px;
      color: $primary;
      flex-shrink: 0;
    }
    .file-name {
      font-size: 12px;
      color: $text;
      max-width: 180px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
  }
}

.tool-row {
  margin-bottom: 4px;

  .msg-content {
    max-width: 100%;
    flex: 1;
  }
}

.tool-card {
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  overflow: hidden;

  &.tool-ok {
    border-color: #e5e7eb;
  }
  &.tool-fail {
    border-color: #fca5a5;
  }

  .tool-header {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 5px 10px;
    cursor: pointer;
    user-select: none;
    transition: background 0.1s;

    &:hover {
      background: #f9fafb;
    }
  }

  .tool-name {
    flex: 1;
    font-size: 11.5px;
    color: #6b7280;
    font-family: 'SF Mono', 'Fira Code', 'Consolas', monospace;
  }

  .tool-status {
    font-size: 10.5px;
    font-weight: 500;
    flex-shrink: 0;

    &.pending {
      color: #9ca3af;
    }
    &.ok {
      color: #9ca3af;
    }
    &.fail {
      color: #ef4444;
    }
  }

  .tool-chevron {
    color: #d1d5db;
    flex-shrink: 0;
    transition: transform 0.15s;
    &.rotated {
      transform: rotate(180deg);
    }
  }

  .tool-body {
    border-top: 1px solid #f3f4f6;
  }

  .tool-result {
    margin: 0;
    padding: 6px 10px;
    border-radius: 0;
    font-size: 11px;
    line-height: 1.5;
    white-space: pre-wrap;
    word-break: break-all;
    max-height: 160px;
    overflow-y: auto;
    background: #fafafa;
    color: #6b7280;
    font-family: 'SF Mono', 'Fira Code', 'Consolas', monospace;

    &.fail {
      background: #fef5f5;
      color: #991b1b;
    }
  }
}

// ── Code block ──

.code-block {
  margin-top: 6px;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  overflow: hidden;
  background: #1e293b;

  .code-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 6px 12px;
    background: #334155;
    border-bottom: 1px solid #475569;
  }
  .code-lang {
    font-size: 11px;
    font-weight: 600;
    color: #94a3b8;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    font-family: 'Fira Code', 'Consolas', monospace;
  }
  .code-copy-btn {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 2px 8px;
    font-size: 11px;
    color: #94a3b8;
    cursor: pointer;
    border-radius: 5px;
    transition: all 0.15s;
    &:hover {
      color: #e2e8f0;
      background: rgba(255, 255, 255, 0.08);
    }
  }
  .code-body {
    margin: 0;
    padding: 12px;
    overflow-x: auto;
    code {
      font-family: 'Fira Code', 'Consolas', monospace;
      font-size: 12.5px;
      line-height: 1.6;
      color: #e2e8f0;
      white-space: pre;
    }
  }
}

// ── Inline citations [1] [2] ────────────────────────────
:deep(.cite-num) {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 16px;
  height: 16px;
  padding: 0 3px;
  margin: 0 1px;
  font-size: 10px;
  font-weight: 600;
  line-height: 1;
  color: #4f46e5;
  background: #eef2ff;
  border: 1px solid #e0e7ff;
  border-radius: 8px;
  cursor: pointer;
  vertical-align: super;
  transition: background 0.12s, border-color 0.12s;

  &:hover {
    background: #ddd6fe;
    border-color: #c4b5fd;
  }
}

// ── Message editing ──────────────────────────────────────
.msg-edit-row {
  display: flex;
  flex-direction: column;
  gap: 4px;
  width: 100%;
  max-width: 420px;
}
.msg-edit-input {
  width: 100%;
  min-height: 48px;
  padding: 8px 12px;
  border: 2px solid $primary;
  border-radius: 10px;
  font-size: 14px;
  font-family: inherit;
  line-height: 1.5;
  resize: vertical;
  outline: none;
  background: var(--color-surface, #fff);
  color: var(--color-text, #1e293b);
  &:focus {
    border-color: color.adjust($primary, $lightness: -8%);
  }
}
.msg-edit-hint {
  font-size: 11px;
  color: $text-muted;
  padding-left: 4px;
}
</style>
