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
        @translate="onShowTranslate"
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
          <div v-if="!isEditing" class="msg-actions">
            <span class="msg-copy" title="复制" @click="$emit('copy', message.text || '')"><CopyOutlined /></span>
            <span
              class="msg-quote-btn"
              title="引用"
              @click="$emit('quote', { text: message.text || '', msgId: message.id, role: 'user' })"
            >
              <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M9 17L4 12l5-5" />
                <path d="M4 12h10a6 6 0 010 12" />
              </svg>
            </span>
            <template v-if="!selectable">
              <span class="msg-select-trigger" title="选择" @click="$emit('startSelect', message.id)">
                <CheckSquareOutlined />
              </span>
            </template>
          </div>
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
        @translate="onShowTranslate"
        @quote="emit('quoteMsg', message.id)"
        @delete="emit('delete', message.id)"
      >
        <div class="msg-content" @contextmenu="onContextMenu">
          <ThinkCard v-if="message.thinking" :content="message.thinking" :thinking="!message.text" />
          <div class="msg-bubble assistant">
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
                  <pre class="code-body"><code>{{ seg.content }}</code></pre>
                </div>
              </template>
            </template>
          </div>
          <MsgReferenceCard :references="message.references" @selectRefs="refs => $emit('selectRefs', refs)" />
          <div class="msg-actions">
            <span class="msg-copy" title="复制" @click="$emit('copy', message.text || '')"><CopyOutlined /></span>
            <span
              class="msg-quote-btn"
              title="引用"
              style="transform: scaleX(-1)"
              @click="$emit('quote', { text: message.text || '', msgId: message.id, role: 'agent' })"
            >
              <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M9 17L4 12l5-5" />
                <path d="M4 12h10a6 6 0 010 12" />
              </svg>
            </span>
            <span class="msg-feedback" :class="fbClass">
              <span class="fb-btn" title="有帮助" @click="onFeedBack('liked')"><LikeOutlined /></span>
              <span class="fb-btn" title="无帮助" @click="onFeedBack('disliked')"><DislikeOutlined /></span>
            </span>
            <template v-if="ttsSupported">
              <span
                class="msg-speak"
                :class="{ active: ttsSpeaking }"
                :title="ttsSpeaking ? '停止朗读' : '朗读'"
                @click="onToggleSpeak"
              >
                <template v-if="!ttsSpeaking"><SoundOutlined /></template>
                <template v-else><PauseCircleFilled /></template>
              </span>
            </template>
            <template v-if="!selectable">
              <span class="msg-select-trigger" title="选择" @click="$emit('startSelect', message.id)"
                ><CheckSquareOutlined
              /></span>
            </template>
          </div>
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
      <div class="msg-avatar tool-av">🔧</div>
      <div class="msg-content">
        <div class="tool-card" :class="{ expanded: toolExpanded }">
          <div class="tool-header" @click="onToggleTool">
            <span class="tool-icon">{{ toolIcon }}</span>
            <span class="tool-name">{{ message.tool.name }}</span>
            <template v-if="message.tool.success === undefined">
              <span class="tool-badge pending">执行中</span>
            </template>
            <template v-else-if="message.tool.success">
              <span class="tool-badge ok">完成</span>
            </template>
            <template v-else>
              <span class="tool-badge fail">失败</span>
            </template>
            <template v-if="message.tool.result !== undefined">
              <span class="tool-expand-icon">{{ toolExpanded ? '▾' : '▸' }}</span>
            </template>
          </div>
          <template v-if="toolExpanded && message.tool.result !== undefined">
            <div class="tool-detail">
              <pre class="tool-result" :class="{ fail: !message.tool.success }">{{ formattedToolResult }}</pre>
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

  <!-- Image preview lightbox -->
  <Teleport to="body">
    <transition name="lightbox-fade">
      <div v-if="previewSrc" class="lightbox-overlay" @click="previewSrc = ''">
        <img :src="previewSrc" class="lightbox-img" @click.stop />
        <span class="lightbox-close" @click="previewSrc = ''">✕</span>
      </div>
    </transition>
  </Teleport>

  <!-- Text selection floating toolbar -->
  <Teleport to="body">
    <transition name="quote-fade">
      <template v-if="quoteVisible">
        <div class="selection-toolbar" :style="{ left: `${quotePos.x}px`, top: `${quotePos.y}px` }">
          <span class="toolbar-btn" @click.stop="onQuoteSelection">
            <svg
              viewBox="0 0 24 24"
              width="14"
              height="14"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              style="transform: scale(-1, -1)"
            >
              <path d="M9 17L4 12l5-5" />
              <path d="M4 12h10a6 6 0 010 12" />
            </svg>
            <span>引用</span>
          </span>
          <span class="toolbar-divider"></span>
          <span class="toolbar-btn" @click.stop="onCopySelection">
            <CopyOutlined />
            <span>复制</span>
          </span>
          <span class="toolbar-divider"></span>
          <span class="toolbar-btn" @click.stop="onTranslateSelection">
            <TranslationOutlined />
            <span>翻译</span>
          </span>
          <template v-if="ttsSupported">
            <span class="toolbar-divider"></span>
            <span class="toolbar-btn" @click.stop="onSpeakSelection">
              <SoundOutlined />
              <span>朗读</span>
            </span>
          </template>
        </div>
      </template>
    </transition>
  </Teleport>

  <template v-if="tlPos">
    <TranslatePopover
      :x="tlPos.x"
      :y="tlPos.y"
      :loading="tlLoading"
      :error="tlError"
      :translated="tlResult"
      :engine="tlEngine"
      :source-lang="tlSrcLang"
      :target-lang="tlTgtLang"
      @close="onCloseTranslate"
      @change-target="onChangeTargetLang"
    />
  </template>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import {
  CopyOutlined,
  CheckSquareOutlined,
  LikeOutlined,
  DislikeOutlined,
  ReloadOutlined,
  FileTextOutlined,
  SoundOutlined,
  PauseCircleFilled,
  TranslationOutlined,
} from '@ant-design/icons-vue'
import type { ChatMessage } from '@/composables/useAgentChat'
import { useSpeech } from '@/composables/useSpeech'
import FileCard from './FileCard.vue'
import MindMapCard from './MindMapCard.vue'
import MapCard from '@/components/shared/MapCard.vue'
import RouteCard from '@/components/shared/RouteCard.vue'
import CanvasPreview from './CanvasPreview.vue'
import TranslatePopover from './TranslatePopover.vue'
import ThinkCard from './ThinkCard.vue'
import MsgContextMenu from './MsgContextMenu.vue'
import MsgReferenceCard from './MsgReferenceCard.vue'

const props = defineProps<{
  message: ChatMessage
  renderMd: (text: string) => string
  selectable?: boolean
  selected?: boolean
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

const toolIcon = computed(() => {
  const name = props.message.tool?.name || ''
  if (name.includes('canvas')) return '▦'
  if (name.includes('file') || name.includes('excel')) return '▤'
  if (name.includes('blueprint')) return '▥'
  if (name.includes('search')) return '⌕'
  return '◆'
})

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

// ── Message segments (mindmap / map / route / code detection) ──

const BLOCK_RE = /```(\w*)\s*\n?([\s\S]*?)```/g

type BlockType = 'mindmap' | 'map' | 'route' | 'files'

interface MsgSegment {
  type: 'text' | BlockType | 'code'
  content?: string
  data?: any
  language?: string
}

const messageSegments = computed(() => {
  const text = props.message.text || ''
  BLOCK_RE.lastIndex = 0
  const segments: MsgSegment[] = []
  let lastIndex = 0
  let match: RegExpExecArray | null
  while ((match = BLOCK_RE.exec(text)) !== null) {
    if (match.index > lastIndex) {
      segments.push({ type: 'text', content: text.slice(lastIndex, match.index) })
    }
    const blockType = match[1]
    const blockContent = match[2].trim()
    if (blockType === 'mindmap') {
      segments.push({ type: 'mindmap', content: blockContent })
    } else if (blockType === 'map' || blockType === 'route' || blockType === 'files') {
      try {
        const data = JSON.parse(blockContent)
        segments.push({ type: blockType as BlockType, data })
      } catch {
        segments.push({ type: 'code', language: blockType, content: blockContent })
      }
    } else {
      segments.push({ type: 'code', language: blockType, content: blockContent })
    }
    lastIndex = match.index + match[0].length
  }
  if (lastIndex < text.length) {
    segments.push({ type: 'text', content: text.slice(lastIndex) })
  }
  return segments.length > 0 ? segments : [{ type: 'text', content: text }]
})

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
  return props.renderMd(text)
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
  onShowTranslate()
}

// ── Translation ───────────────────────────────────────────
const tlLoading = ref(false)
const tlError = ref('')
const tlResult = ref('')
const tlEngine = ref('')
const tlSrcLang = ref('')
const tlTgtLang = ref('zh')
const tlPos = ref<{ x: number; y: number } | null>(null)
let tlText = ''

function detectTextLang(text: string): string {
  // Count CJK characters
  const cjk = (text.match(/[一-鿿㐀-䶿]/g) || []).length
  const total = text.replace(/\s/g, '').length
  return cjk > total * 0.3 ? 'zh' : 'en'
}

async function onTranslate(targetLang?: string) {
  const text = window.getSelection()?.toString().trim()
  if (!text) return
  tlText = text
  const target = targetLang || (detectTextLang(text) === 'zh' ? 'en' : 'zh')
  tlLoading.value = true
  tlError.value = ''
  tlResult.value = ''
  try {
    const { translateText } = await import('@/api/translate')
    const res = await translateText({ text, target_lang: target, source_lang: 'auto' })
    tlResult.value = res.translated
    tlEngine.value = res.engine
    tlSrcLang.value = res.source_lang
    tlTgtLang.value = res.target_lang
  } catch (e: any) {
    tlError.value = e.message || '翻译失败'
  } finally {
    tlLoading.value = false
  }
}

function onShowTranslate() {
  const sel = window.getSelection()
  if (sel?.rangeCount) {
    const rect = sel.getRangeAt(0).getBoundingClientRect()
    tlPos.value = { x: rect.left + rect.width / 2 - 170, y: rect.bottom }
    onTranslate()
  }
}

async function onChangeTargetLang(lang: string) {
  tlTgtLang.value = lang
  tlLoading.value = true
  tlError.value = ''
  tlResult.value = ''
  try {
    const { translateText } = await import('@/api/translate')
    const res = await translateText({ text: tlText, target_lang: lang, source_lang: 'auto' })
    tlResult.value = res.translated
    tlEngine.value = res.engine
    tlSrcLang.value = res.source_lang
    tlTgtLang.value = res.target_lang
  } catch (e: any) {
    tlError.value = e.message || '翻译失败'
  } finally {
    tlLoading.value = false
  }
}

function onCloseTranslate() {
  tlPos.value = null
  tlText = ''
  tlLoading.value = false
  tlError.value = ''
  tlResult.value = ''
  tlEngine.value = ''
  tlSrcLang.value = ''
}

// ── End Translation ───────────────────────────────────────

onMounted(() => {
  document.addEventListener('click', hideContextMenu)
})

onBeforeUnmount(() => {
  document.removeEventListener('click', hideContextMenu)
})
</script>

<style lang="scss" scoped>
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
    &.tool-av {
      background: #fef3c7;
      color: #d97706;
      font-size: 14px;
    }
  }

  .msg-content {
    max-width: 75%;
    min-width: 0;
  }

  &.tool-row .msg-content {
    max-width: 92%;
    flex: 1;
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

  .msg-actions {
    display: flex;
    align-items: center;
    gap: 2px;
    margin-top: 4px;
  }

  .msg-copy,
  .msg-quote-btn,
  .msg-select-trigger {
    display: inline-flex;
    align-items: center;
    padding: 3px 6px;
    font-size: 12px;
    color: $text-muted;
    cursor: pointer;
    border-radius: 4px;
    transition: all 0.15s;
    opacity: 0;
    &:hover {
      color: $primary;
      background: #f1f5f9;
    }
  }

  .msg-speak {
    display: inline-flex;
    align-items: center;
    padding: 3px 6px;
    font-size: 12px;
    color: $text-muted;
    cursor: pointer;
    border-radius: 4px;
    transition: all 0.15s;
    opacity: 0;
    &:hover {
      color: $primary;
      background: #f1f5f9;
    }
    &.active {
      opacity: 1;
      color: $primary;
      background: #eef2ff;
    }
  }

  .msg-feedback {
    display: inline-flex;
    align-items: center;
    gap: 2px;
    opacity: 0;
    .fb-btn {
      display: inline-flex;
      align-items: center;
      padding: 3px 5px;
      font-size: 12px;
      color: $text-muted;
      cursor: pointer;
      border-radius: 4px;
      transition: all 0.15s;
      &:hover {
        color: $primary;
        background: #f1f5f9;
      }
    }
    &.liked,
    &.disliked {
      opacity: 1;
    }
    &.liked .fb-btn:first-child {
      color: $primary;
    }
    &.disliked .fb-btn:last-child {
      color: #dc2626;
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

  &:hover .msg-copy,
  &:hover .msg-speak,
  &:hover .msg-feedback,
  &:hover .msg-select-trigger,
  &:hover .msg-quote-btn {
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
    transition:
      transform 0.15s,
      border-color 0.15s;
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

.tool-card {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 6px 10px;
  font-size: 12px;
  .tool-header {
    display: flex;
    align-items: center;
    gap: 6px;
    cursor: pointer;
    user-select: none;
  }
  .tool-icon {
    font-size: 13px;
    color: #64748b;
    flex-shrink: 0;
  }
  .tool-name {
    font-weight: 500;
    color: #475569;
    font-family: 'Fira Code', 'Consolas', monospace;
    font-size: 11px;
  }
  .tool-badge {
    font-size: 10px;
    padding: 0 6px;
    border-radius: 6px;
    font-weight: 500;
    line-height: 18px;
    &.pending {
      background: #dbeafe;
      color: #1e40af;
    }
    &.ok {
      background: #d1fae5;
      color: #065f46;
    }
    &.fail {
      background: #fee2e2;
      color: #991b1b;
    }
  }
  .tool-expand-icon {
    margin-left: auto;
    font-size: 10px;
    color: #94a3b8;
  }
  .tool-detail {
    margin-top: 6px;
    padding-top: 6px;
    border-top: 1px solid #e2e8f0;
  }
  .tool-result {
    margin: 0;
    padding: 8px;
    border-radius: 6px;
    font-size: 11px;
    line-height: 1.5;
    white-space: pre-wrap;
    word-break: break-all;
    max-height: 180px;
    overflow-y: auto;
    background: #f1f5f9;
    color: #334155;
    &.fail {
      background: #fef2f2;
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

// ── Text selection floating toolbar ──

.selection-toolbar {
  position: fixed;
  z-index: 999;
  display: flex;
  align-items: center;
  padding: 4px 6px;
  background: #fff;
  border-radius: 10px;
  box-shadow:
    0 4px 20px rgba(79, 70, 229, 0.12),
    0 2px 8px rgba(0, 0, 0, 0.06),
    0 0 0 0.5px rgba(0, 0, 0, 0.06);
  transform: none;
  transition:
    box-shadow 0.2s,
    transform 0.15s;
  user-select: none;

  .toolbar-btn {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 4px 10px;
    font-size: 13px;
    font-weight: 500;
    color: #333;
    cursor: pointer;
    border-radius: 6px;
    transition: background 0.12s;
    &:hover {
      background: rgba(79, 70, 229, 0.06);
    }
    &:active {
      transform: scale(0.96);
    }
  }
  .toolbar-divider {
    width: 1px;
    height: 18px;
    background: #e2e8f0;
    margin: 0 2px;
  }
}

.quote-fade-enter-active,
.quote-fade-leave-active {
  transition: opacity 0.12s ease;
}
.quote-fade-enter-from,
.quote-fade-leave-to {
  opacity: 0;
}

// ── Image preview lightbox ──

.lightbox-overlay {
  position: fixed;
  inset: 0;
  z-index: 2000;
  background: rgba(0, 0, 0, 0.72);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  .lightbox-img {
    max-width: 90vw;
    max-height: 90vh;
    border-radius: 8px;
    box-shadow: 0 8px 40px rgba(0, 0, 0, 0.3);
    cursor: default;
  }
  .lightbox-close {
    position: absolute;
    top: 16px;
    right: 20px;
    width: 36px;
    height: 36px;
    border-radius: 50%;
    background: rgba(255, 255, 255, 0.15);
    color: #fff;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 18px;
    cursor: pointer;
    transition: background 0.15s;
    &:hover {
      background: rgba(255, 255, 255, 0.25);
    }
  }
}

.lightbox-fade-enter-active,
.lightbox-fade-leave-active {
  transition: opacity 0.2s ease;
}
.lightbox-fade-enter-from,
.lightbox-fade-leave-to {
  opacity: 0;
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
    border-color: darken($primary, 8%);
  }
}
.msg-edit-hint {
  font-size: 11px;
  color: $text-muted;
  padding-left: 4px;
}
</style>
