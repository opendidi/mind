<!-- Mind AI Chat — full page chat view -->
<template>
  <div class="ds-chat-page">
    <!-- Sidebar -->
    <ChatSidebar
      :conversations="conversations"
      :activeConvId="activeConvId"
      :collapsed="sidebarCollapsed"
      :messagesCount="messages.length"
      :hasMore="hasMoreConversations"
      @update:collapsed="sidebarCollapsed = $event"
      @new-chat="onNewChat"
      @select="onSwitchConv"
      @delete="onDeleteConv"
      @clear="onClearData"
      @togglePin="onTogglePin"
      @loadMore="onLoadMoreConversations"
      @export="onExportConv"
    />

    <!-- Main chat area -->
    <main class="chat-main">
      <!-- Header -->
      <header class="chat-header">
        <div class="header-left">
          <a-button type="text" class="header-icon-btn" @click="sidebarCollapsed = !sidebarCollapsed">
            <template v-if="sidebarCollapsed">
              <MenuUnfoldOutlined />
            </template>
            <template v-else>
              <MenuFoldOutlined />
            </template>
          </a-button>
          <span class="header-divider" />
          <span class="header-title">
            {{ activeConvTitle || 'AI 对话' }}
          </span>
        </div>
        <div class="header-right">
          <template v-if="streamDisconnected">
            <span class="header-status disconnected" @click="onRetry" title="点击重连">
              <span class="status-dot" /> 连接断开
            </span>
          </template>
          <template v-else-if="loading || switchingConv">
            <span class="header-status working"> <span class="status-dot" /> 处理中 </span>
          </template>
          <template v-else-if="messages.length > 0">
            <span class="header-status idle"> <span class="status-dot" /> 就绪 </span>
          </template>
          <a-button class="header-icon-btn" size="small" type="text" @click="onNewChat" title="新建对话">
            <PlusOutlined />
          </a-button>
          <a-button class="header-icon-btn" size="small" type="text" @click="openFileManager" title="文件管理">
            <FolderOpenOutlined />
          </a-button>
          <a-button
            class="header-icon-btn"
            size="small"
            type="text"
            @click="toggleTheme"
            :title="isDark ? '浅色模式' : '深色模式'"
          >
            {{ isDark ? '☀️' : '🌙' }}
          </a-button>
          <span class="user-avatar">{{ userName.charAt(0) || 'U' }}</span>
        </div>
      </header>

      <!-- Message search bar (Ctrl+K) -->
      <template v-if="searchVisible">
        <div class="search-bar">
          <input
            ref="searchInputRef"
            v-model="searchQuery"
            class="search-input"
            placeholder="搜索消息… Enter 跳转 · Esc 关闭"
            @keydown="onSearchKeydown"
          />
          <template v-if="searchQuery">
            <span class="search-count">
              {{ searchMatchIdx >= 0 ? `${searchMatchIdx + 1}/${searchMatches.length}` : '无结果' }}
            </span>
          </template>
          <a-button size="small" type="text" @click="searchVisible = false">✕</a-button>
        </div>
      </template>

      <!-- Messages area -->
      <div ref="msgListRef" class="msg-area" @scroll="onMsgAreaScroll">
        <!-- Empty state -->
        <template v-if="messages.length === 0 && !loading && !switchingConv">
          <WelcomePanel @suggest="onSuggestion" />
        </template>

        <!-- Plan card -->
        <PlanCard :plan="currentPlan" />

        <!-- Messages -->
        <div class="msg-inner">
          <template v-for="item in groupedMessages" :key="Array.isArray(item) ? 'tg-' + item[0].id : item.id">
            <!-- Tool group (2+ consecutive tool calls) -->
            <template v-if="Array.isArray(item) && item.length > 1">
              <details class="tool-group-details">
                <summary class="tool-group-summary">
                  <span class="tg-label">工具调用 ({{ item.length }})</span>
                  <svg class="tg-chevron" viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2"><path d="M6 9l6 6 6-6"/></svg>
                </summary>
                <div class="tool-group-body">
                  <template v-for="m in item" :key="m.id">
                    <MsgRow
                      :message="m"
                      :renderMd="renderMd"
                      :selectable="selectMode"
                      :streaming="isStreamingMsg(m)"
                      :selected="selectedIds.has(m.id)"
                      @copy="copyText"
                      @toggleSelect="onToggleSelect"
                      @startSelect="onStartSelect"
                      @feedback="onMsgFeedback"
                      @quote="onQuoteMsg"
                      @quoteMsg="onQuoteMsgId"
                      @delete="onDeleteMsg"
                      @retry="onRetry"
                      @edit="onMsgEdit"
                      @selectRefs="onSelectRefs"
                    />
                  </template>
                </div>
              </details>
            </template>
            <!-- Single message (or single tool) -->
            <template v-else>
              <MsgRow
                :message="Array.isArray(item) ? item[0] : item"
                :renderMd="renderMd"
                :selectable="selectMode"
                :streaming="isStreamingMsg(Array.isArray(item) ? item[0] : item)"
                :selected="selectedIds.has(Array.isArray(item) ? item[0].id : item.id)"
                @copy="copyText"
                @toggleSelect="onToggleSelect"
                @startSelect="onStartSelect"
                @feedback="onMsgFeedback"
                @quote="onQuoteMsg"
                @quoteMsg="onQuoteMsgId"
                @delete="onDeleteMsg"
                @retry="onRetry"
                @edit="onMsgEdit"
                @selectRefs="onSelectRefs"
              />
            </template>
          </template>

          <!-- Minimal streaming indicator (only when no messages being actively streamed) -->
          <template v-if="(loading || switchingConv) && !hasLiveThinking && !hasStreamingText">
            <div class="msg-row loading-indicator">
              <div class="load-dot-pulse" />
              <span class="load-label">{{ loadingStatus }}</span>
            </div>
          </template>
        </div>
        <div ref="msgEndRef" />
      </div>

      <!-- Scroll-to-bottom FAB -->
      <transition name="fab-fade">
        <template v-if="!isNearBottom">
          <div class="scroll-fab" @click="scrollToBottom(true)">
            <span class="fab-icon">↓</span>
          </div>
        </template>
      </transition>

      <!-- Selection toolbar -->
      <template v-if="messages.length > 0 && selectMode">
        <div class="select-toolbar">
          <span class="select-count">
            {{ selectedIds.size > 0 ? `已选 ${selectedIds.size} 条` : '选择消息' }}
          </span>
          <a-button size="small" type="text" class="select-all-btn" @click="onSelectAll">
            <CheckSquareOutlined />
          </a-button>
          <div class="select-spacer" />
          <a-button size="small" type="text" class="select-cancel-btn" @click="onCancelSelect">
            <CloseOutlined />
          </a-button>
          <a-button size="small" class="select-del-btn" @click="onBatchDelete" :disabled="selectedIds.size === 0">
            <DeleteOutlined />
          </a-button>
        </div>
      </template>

      <!-- Input area -->
      <!-- File manager selected images preview -->
      <template v-if="fileManagerImages.length > 0">
        <div class="fm-images-bar">
          <span class="fm-images-label">从文件管理器选择的图片：</span>
          <template v-for="(img, idx) in fileManagerImages" :key="img.url">
            <div class="fm-img-tag">
              <img :src="img.url" :alt="img.name" />
              <span class="fm-img-name">{{ img.name }}</span>
              <span class="fm-img-remove" @click="fileManagerImages.splice(idx, 1)">×</span>
            </div>
          </template>
          <a-button size="small" type="link" @click="fileManagerImages = []">清空</a-button>
        </div>
      </template>

      <ChatInput
        :loading="loading || switchingConv"
        :modelList="modelList"
        :modelIdx="activeModelIdx"
        :quotedText="quotedText"
        @update:modelIdx="activeModelIdx = $event"
        @send="onSend"
        @abort="onAbort"
        @removeQuote="quotedText = null"
      />
    </main>

    <!-- Canvas preview panel (shown when agent modified canvas) -->
    <template v-if="showCanvasPreview">
      <aside class="canvas-preview-panel">
        <div class="preview-header">
          <span class="preview-title">画布预览</span>
          <div class="preview-actions">
            <a-button size="small" type="link" @click="openCanvasEditor"> 打开编辑器 </a-button>
            <a-button size="small" type="text" @click="showCanvasPreview = false"> ✕ </a-button>
          </div>
        </div>
        <iframe ref="previewIframe" class="preview-iframe" :src="previewUrl" @load="onPreviewLoaded" />
      </aside>
    </template>

    <!-- Canvas preview toggle (when hidden but changes exist) -->
    <transition name="fab-fade">
      <template v-if="!showCanvasPreview && hasCanvasChanges">
        <div class="canvas-preview-fab" @click="showCanvasPreview = true" title="查看画布修改">
          <span class="fab-badge" />
          <span class="fab-label">画布</span>
        </div>
      </template>
    </transition>

    <FileManager ref="fileManagerRef" mode="multiple" @oks="onFileManagerOk" />
    <ReferencePanel :visible="refPanelVisible" :references="refPanelData" @close="onCloseRefPanel" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import { message } from 'ant-design-vue'
import {
  MenuUnfoldOutlined,
  MenuFoldOutlined,
  DeleteOutlined,
  CheckSquareOutlined,
  CloseOutlined,
  FolderOpenOutlined,
  PlusOutlined,
} from '@ant-design/icons-vue'
import { useRouter, useRoute } from 'vue-router'
import MarkdownIt from 'markdown-it'
import { useUserStore } from '@/store/modules/user'
import { useAgentChat, type QuoteInfo, type ChatFile, type ChatMessage } from '@/composables/useAgentChat'
import { useConversations } from '@/composables/useConversations'
import { useMessageSelect } from '@/composables/useMessageSelect'
import { useScrollToBottom } from '@/composables/useScrollToBottom'
import { useTheme } from '@/composables/useTheme'
import { executeCanvasTool } from '@/utils/canvasBridge'
import { apiBlueprintModify } from '@/api/blueprint'
import ChatSidebar from '@/components/chat/ChatSidebar.vue'
import ChatInput from '@/components/chat/ChatInput.vue'
import PlanCard from '@/components/chat/PlanCard.vue'
import MsgRow from '@/components/chat/MsgRow.vue'
import WelcomePanel from '@/components/chat/WelcomePanel.vue'
import FileManager from '@/components/FileManager/index.vue'
import ReferencePanel from '@/components/chat/ReferencePanel.vue'

const md = new MarkdownIt({
  html: false,
  linkify: true,
  typographer: true,
  breaks: true,
})
const renderMd = (text: string) => md.render(text)

const router = useRouter()
const route = useRoute()
const userName = computed(() => '用户')
const { isDark, toggleTheme } = useTheme()

// UI state
const sidebarCollapsed = ref(false)
const quotedText = ref<QuoteInfo | null>(null)
const fileManagerRef = ref<InstanceType<typeof FileManager>>()
const fileManagerImages = ref<Array<{ name: string; url: string }>>([])

// ── Message search ───────────────────────────────────────
const searchVisible = ref(false)
const searchQuery = ref('')
const searchInputRef = ref<HTMLInputElement>()
const searchMatchIdx = ref(-1)

const searchMatches = computed(() => {
  if (!searchQuery.value.trim()) return []
  const q = searchQuery.value.toLowerCase()
  const results: Array<{ msgId: string; role: string; text: string; startIdx: number }> = []
  for (const m of messages.value) {
    if (!m.text) continue
    const idx = m.text.toLowerCase().indexOf(q)
    if (idx >= 0) {
      results.push({ msgId: m.id, role: m.role, text: m.text, startIdx: idx })
    }
  }
  return results
})

function openSearch() {
  searchVisible.value = true
  searchQuery.value = ''
  searchMatchIdx.value = -1
  requestAnimationFrame(() => searchInputRef.value?.focus())
}

function onSearchKeydown(e: KeyboardEvent) {
  if (e.key === 'Escape') {
    searchVisible.value = false
    return
  }
  if (e.key === 'Enter') {
    e.preventDefault()
    if (searchMatches.value.length > 0) {
      searchMatchIdx.value = (searchMatchIdx.value + 1) % searchMatches.value.length
      const match = searchMatches.value[searchMatchIdx.value]
      const el = document.querySelector(`[data-msg-id="${match.msgId}"]`)
      el?.scrollIntoView({ behavior: 'smooth', block: 'center' })
    }
  }
}

// ── Keyboard shortcuts ───────────────────────────────────
function onPageKeydown(e: KeyboardEvent) {
  // Don't capture when typing in inputs
  const tag = (e.target as HTMLElement).tagName
  if (tag === 'INPUT' || tag === 'TEXTAREA' || (e.target as HTMLElement).isContentEditable) return
  const mod = e.ctrlKey || e.metaKey

  if (mod && e.key === 'n') {
    e.preventDefault()
    onNewChat()
    return
  }
  if (mod && e.key === 'k') {
    e.preventDefault()
    openSearch()
    return
  }
  if (e.key === 'Escape') {
    if (selectMode.value) onCancelSelect()
    if (refPanelVisible.value) onCloseRefPanel()
    if (searchVisible.value) searchVisible.value = false
    return
  }
  if (mod && e.key === 'ArrowUp') {
    e.preventDefault()
    const lastUser = [...messages.value].reverse().find(m => m.role === 'user')
    if (lastUser) {
      const el = document.querySelector(`[data-msg-id="${lastUser.id}"]`)
      if (el) (el as HTMLElement).dispatchEvent(new MouseEvent('dblclick'))
    }
  }
}

function openFileManager() {
  fileManagerRef.value!.visible = true
  fileManagerRef.value!.init()
  fileManagerRef.value!.initMaterialFolder()
}

// Canvas preview
const CANVAS_TOOLS = [
  'add_pen',
  'canvas_add_pen',
  'add_line',
  'canvas_add_line',
  'update_pen',
  'canvas_update_pen',
  'delete_pen',
  'canvas_delete_pen',
  'clear',
  'canvas_clear',
  'add_diagram',
  'canvas_add_diagram',
  'layout_auto_arrange',
  'layout_align',
]
const hasCanvasChanges = ref(false)
const showCanvasPreview = ref(false)
const previewIframe = ref<HTMLIFrameElement>()
const previewUrl = `${window.location.origin}${window.location.pathname}#/preview`

function onPreviewLoaded() {
  // iframe loaded — canvas is displayed
}

function openCanvasEditor() {
  window.open(`${window.location.origin}${window.location.pathname}#/`, '_blank')
}

// Plan state — driven by composable's built-in plan tracker
const currentPlan = computed(() => {
  const p = plan.value
  if (!p) return null
  return {
    goal: p.goal,
    risk: p.risk,
    steps: p.nodes.map(n => ({
      id: n.id,
      desc: n.desc,
      tool: null as string | null,
      confirm: n.confirm ?? false,
      status: n.status,
    })),
  }
})

// Loading status labels
const TOOL_LABELS: Record<string, string> = {
  create_pen: '创建图形',
  delete_pen: '删除图形',
  update_pen: '更新图形',
  move_pen: '移动图形',
  layout: '自动排版',
  create_mindmap: '生成思维导图',
  search_blueprints: '搜索蓝图',
  load_blueprint: '加载蓝图',
  web_search: '搜索网络信息',
}

const loadingStatus = computed(() => {
  if (!loading.value) return ''
  if (thinkingText.value) return thinkingText.value
  if (currentTool.value) {
    const label = TOOL_LABELS[currentTool.value] || currentTool.value
    return `正在${label}`
  }
  if (currentPlan.value) return '分析任务中'
  return 'AI 思考中'
})

// Whether there's a live thinking message currently being streamed (DeepSeek-R1 style)
const hasLiveThinking = computed(() => {
  if (!loading.value) return false
  const msgs = messages.value
  if (msgs.length === 0) return false
  const last = msgs[msgs.length - 1]
  return last.role === 'agent' && last.thinkingActive === true
})

// Whether answer text is actively being streamed (tokens arriving in real-time)
const hasStreamingText = computed(() => {
  if (!loading.value) return false
  const msgs = messages.value
  if (msgs.length === 0) return false
  const last = msgs[msgs.length - 1]
  // Agent message with text content (not just thinking) while still loading
  return last.role === 'agent' && typeof last.text === 'string' && last.text.length > 0
})

// Check if a specific message is the one currently being streamed
function isStreamingMsg(msg: ChatMessage): boolean {
  if (!loading.value) return false
  const msgs = messages.value
  if (msgs.length === 0) return false
  // Only the last message can be streaming
  const last = msgs[msgs.length - 1]
  return msg.id === last.id && last.role === 'agent' && typeof last.text === 'string'
}

// Group consecutive tool messages into collapsible blocks
const groupedMessages = computed(() => {
  const result: Array<ChatMessage | ChatMessage[]> = []
  let toolGroup: ChatMessage[] = []
  for (const msg of messages.value) {
    if (msg.role === 'tool') {
      toolGroup.push(msg)
    } else {
      if (toolGroup.length > 0) {
        result.push([...toolGroup])
        toolGroup = []
      }
      result.push(msg)
    }
  }
  if (toolGroup.length > 0) result.push([...toolGroup])
  return result
})

// Models
const modelList = ref<{ id: string }[]>([])
const activeModelIdx = ref(0)

watch(activeModelIdx, val => {
  if (modelList.value[val]) localStorage.setItem('chat-model-idx', String(val))
})

// Deferred save hooks — avoid TDZ: useAgentChat runs before useConversations
// but its callbacks reference saveCurrentConv / silentSave.
const _saveHooks: { onDone?: () => void; onStreamTick?: () => void } = {}

// Agent composable — plan / tool calls / SSE events handled centrally
const {
  messages,
  loading,
  currentTool,
  thinkingText,
  plan,
  streamDisconnected,
  send: agentSend,
  abort: agentAbort,
  retry: agentRetry,
  clear: agentClear,
} = useAgentChat({
  userId: useUserStore().userInfo?.id || undefined,
  onToolResult(tool, args, success, result) {
    executeCanvasTool(tool, args as Record<string, unknown>, success, result)
    if (success && CANVAS_TOOLS.includes(tool)) {
      hasCanvasChanges.value = true
      showCanvasPreview.value = true
      // Notify the preview iframe to reload (canvas was mutated via localStorage)
      if (previewIframe.value?.contentWindow) {
        previewIframe.value.contentWindow.postMessage({ type: 'canvas:mutated' }, '*')
      }
    }
    // When Agent saves a blueprint, inject the actual canvas data from localStorage
    // (the backend doesn't have access to the frontend's Meta2D state)
    if (success && tool === 'blueprint_save') {
      const blueprintId = (result as any)?.data?.id
      if (blueprintId) {
        const raw = localStorage.getItem('meta2d')
        if (raw) {
          try {
            const canvasData = JSON.parse(raw)
            // Save the full pens array (nodes) plus lines from localStorage
            // The blueprint's pens column stores the complete Meta2D pen array
            const pens = JSON.stringify(canvasData.pens || [])
            apiBlueprintModify({ id: blueprintId, pens }).catch(e => {
              console.warn('[blueprint_save] failed to sync canvas data:', e)
            })
          } catch (e) {
            console.warn('[blueprint_save] failed to parse localStorage meta2d:', e)
          }
        }
      }
    }
  },
  onDone() {
    _saveHooks.onDone?.()
  },
  onStreamTick() {
    _saveHooks.onStreamTick?.()
  },
})

// Scroll management
const { msgListRef, msgEndRef, isNearBottom, scrollToBottom, onMsgAreaScroll } = useScrollToBottom(messages, loading)

// Conversation management
const {
  conversations,
  activeConvId,
  hasMoreConversations,
  switchingConv,
  activeConvTitle,
  saveCurrentConv,
  silentSave,
  onNewChat,
  onSwitchConv,
  onDeleteConv,
  onTogglePin,
  onLoadMoreConversations,
  onExportConv,
  onClearData,
  loadConversationList,
} = useConversations({
  messages,
  currentPlan,
  agentAbort,
  agentClear,
  router,
  route,
  onLoaded: () => scrollToBottom(true),
})

// Wire deferred save hooks — now that saveCurrentConv / silentSave are initialized
_saveHooks.onDone = saveCurrentConv
_saveHooks.onStreamTick = silentSave

// Multi-select
const { selectMode, selectedIds, onToggleSelect, onStartSelect, onSelectAll, onCancelSelect, onBatchDelete } =
  useMessageSelect(messages, () => saveCurrentConv())

// Message actions
async function copyText(text: string) {
  try {
    await navigator.clipboard.writeText(text)
    message.success('已复制')
  } catch {
    message.error('复制失败')
  }
}

function onQuoteMsg(data: { text: string; msgId: string; role: string }) {
  quotedText.value = {
    text: data.text,
    msgId: data.msgId,
    role: data.role as QuoteInfo['role'],
  }
}

function onQuoteMsgId(msgId: string) {
  const msg = messages.value.find(m => m.id === msgId)
  if (!msg) return
  const text = msg.text || ''
  const role: QuoteInfo['role'] = msg.role === 'user' || msg.role === 'agent' ? msg.role : 'agent'
  quotedText.value = { text, msgId, role }
}

function onDeleteMsg(msgId: string) {
  messages.value = messages.value.filter(m => m.id !== msgId)
  saveCurrentConv()
}

function onMsgEdit(msgId: string, newText: string) {
  const msg = messages.value.find(m => m.id === msgId)
  if (msg && msg.role === 'user') {
    msg.text = newText
    saveCurrentConv()
  }
}

// ── Reference panel ──
const refPanelVisible = ref(false)
const refPanelData = ref<Array<{ title?: string; url: string; snippet?: string; domain?: string }>>([])

function onSelectRefs(refs: Array<{ title?: string; url: string; snippet?: string; domain?: string }>) {
  refPanelData.value = refs
  refPanelVisible.value = true
}

function onCloseRefPanel() {
  refPanelVisible.value = false
}

function onMsgFeedback(_msgId: string, _type: string) {
  // Feedback persistence placeholder
  saveCurrentConv()
}

function onSuggestion(text: string) {
  onSend(text, [], [], [])
}

// File manager selection → image URLs for Agent
const IMG_EXTS = ['png', 'jpg', 'jpeg', 'gif', 'webp', 'svg']
function onFileManagerOk(files: any[]) {
  const images = files
    .filter((f: any) => IMG_EXTS.includes(f.extension?.toLowerCase()))
    .map((f: any) => ({ name: f.name, url: f.url }))
  if (images.length > 0) {
    fileManagerImages.value.push(...images)
    message.success(`已选择 ${images.length} 张图片，发送消息时将一并提交`)
  }
}

// Send
async function onSend(
  text: string,
  imageUrls: string[],
  docMarkers: string[],
  docFiles: ChatFile[],
  quotedTextParam?: QuoteInfo,
) {
  // Merge file-manager selected image URLs with newly uploaded ones
  const fmUrls = fileManagerImages.value.map(img => img.url)
  const allImageUrls = [...imageUrls, ...fmUrls]
  fileManagerImages.value = []

  const hasImages = allImageUrls.length > 0
  const hasDocs = docMarkers.length > 0
  const hasAnyAttach = hasImages || hasDocs
  if ((!text && !hasAnyAttach) || loading.value) return

  // Build API text: doc markers are needed for backend file tools,
  // but image URLs are NOT embedded — they go via the images parameter (vision bridge)
  const parts: string[] = []
  if (hasDocs) parts.push(docMarkers.join('\n'))
  if (text) parts.push(text)
  const apiText = parts.join('\n')

  isNearBottom.value = true
  await agentSend(
    apiText,
    hasImages ? allImageUrls : undefined,
    undefined,
    quotedTextParam,
    hasDocs ? docFiles : undefined,
  )
}

function onAbort() {
  agentAbort()
}
function onRetry() {
  console.log('[chat] onRetry triggered')
  agentRetry()
}

// Lifecycle
onMounted(() => {
  loadConversationList()
  const saved = localStorage.getItem('chat-model-idx')
  if (saved) activeModelIdx.value = Number(saved)
  document.addEventListener('keydown', onPageKeydown)
})

onBeforeUnmount(() => {
  document.removeEventListener('keydown', onPageKeydown)
  if (messages.value.length > 0) silentSave()
  agentAbort()
})
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;

.icon-ds {
  display: block;
  background: linear-gradient(135deg, #818cf8, #c084fc);
  clip-path: polygon(50% 0%, 62% 38%, 100% 50%, 62% 62%, 50% 100%, 38% 62%, 0% 50%, 38% 38%);
  animation: sparkle-pulse 2.4s ease-in-out infinite;
  width: 28px;
  height: 28px;

  &.ds-big {
    width: 56px;
    height: 56px;
  }

  &.ds-small {
    width: 18px;
    height: 18px;
    animation: none;
  }
}

@keyframes sparkle-pulse {
  0%,
  100% {
    opacity: 0.7;
    transform: scale(0.95);
  }

  50% {
    opacity: 1;
    transform: scale(1.05);
  }
}

.ds-chat-page {
  display: flex;
  height: 100vh;
  width: 100vw;
  background: var(--color-bg, $bg);
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, 'PingFang SC',
    'Microsoft YaHei', 'Apple Color Emoji', 'Segoe UI Emoji', 'Noto Color Emoji', sans-serif;
  overflow: hidden;
}

.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  height: 100vh;
  background: var(--color-surface, $surface);
}

.chat-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 16px;
  border-bottom: 1px solid var(--color-border, $border);
  background: var(--color-surface, $surface);
  flex-shrink: 0;
  height: 48px;
  gap: 12px;

  .header-left {
    display: flex;
    align-items: center;
    gap: 8px;
    min-width: 0;
    flex: 1;
  }

  .header-title {
    font-size: 14px;
    font-weight: 600;
    color: var(--color-text, $text);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .header-divider {
    width: 1px;
    height: 20px;
    background: #e2e8f0;
    flex-shrink: 0;
  }

  .header-right {
    display: flex;
    align-items: center;
    gap: 4px;
    flex-shrink: 0;
  }

  .header-icon-btn {
    width: 32px;
    height: 32px;
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #6b7280;
    border: none;
    background: transparent;
    cursor: pointer;
    font-size: 15px;
    transition: all 0.15s;

    &:hover {
      background: #f1f5f9;
      color: #374151;
    }
  }

  .header-status {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 12px;
    font-weight: 500;
    padding: 2px 10px;
    border-radius: 12px;
    margin-right: 6px;

    &.disconnected {
      color: #dc2626;
      background: #fef2f2;
      cursor: pointer;
      &:hover {
        background: #fee2e2;
      }
    }

    &.working {
      color: #b45309;
      background: #fef3c7;
    }

    &.idle {
      color: #64748b;
      background: #f1f5f9;
    }

    .status-dot {
      width: 6px;
      height: 6px;
      border-radius: 50%;
      background: #94a3b8;
    }

    &.disconnected .status-dot {
      background: #ef4444;
      animation: status-blink 0.8s ease-in-out infinite;
    }

    &.working .status-dot {
      background: #f59e0b;
      animation: status-blink 1.2s ease-in-out infinite;
    }
  }

  .user-avatar {
    width: 28px;
    height: 28px;
    border-radius: 50%;
    background: $primary-gradient;
    color: #fff;
    font-size: 12px;
    font-weight: 600;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    margin-left: 4px;
  }
}

@keyframes status-blink {
  0%,
  100% {
    opacity: 1;
  }

  50% {
    opacity: 0.3;
  }
}

// ── Search bar ────────────────────────────────────────────
.search-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 16px;
  background: var(--color-surface, $surface);
  border-bottom: 1px solid var(--color-border, $border);
  flex-shrink: 0;
  .search-input {
    flex: 1;
    border: none;
    outline: none;
    font-size: 13px;
    padding: 4px 0;
    background: transparent;
    color: var(--color-text, $text);
    &::placeholder {
      color: $text-muted;
    }
  }
  .search-count {
    font-size: 12px;
    color: $text-muted;
    white-space: nowrap;
  }
}

.msg-area {
  flex: 1;
  overflow-y: auto;
  scrollbar-gutter: stable;
  padding: 20px 0;
  position: relative;

  .msg-inner {
    max-width: $msg-max-width;
    margin: 0 auto;
    padding: 0 24px;
  }
}

.msg-row {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
  content-visibility: auto;
  contain-intrinsic-size: auto 70px;

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

    &.ai {
      background: linear-gradient(135deg, $primary, #7c3aed);
      color: #fff;

      :deep(.ds-small) {
        filter: brightness(0) invert(1);
      }
    }
  }

  .msg-content {
    max-width: 75%;
    min-width: 0;
  }
}

.select-toolbar {
  display: flex;
  align-items: center;
  gap: 6px;
  max-width: $msg-max-width;
  margin: 0 auto;
  padding: 0 24px 10px;

  .select-count {
    font-size: 13px;
    color: var(--color-text-secondary, $text-secondary);
    font-weight: 500;
    min-width: 60px;
  }

  .select-spacer {
    flex: 1;
  }

  .select-all-btn,
  .select-cancel-btn {
    width: 32px;
    height: 32px;
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 0;
    color: var(--color-text-muted, $text-muted);
    transition: all 0.15s;

    &:hover {
      color: var(--color-text-secondary, $text-secondary);
      background: #f1f5f9;
    }
  }

  .select-del-btn {
    width: 32px;
    height: 32px;
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 0;
    color: var(--color-text-muted, $text-muted);
    background: transparent;
    border: none;
    transition: all 0.15s;

    &:hover:not(:disabled) {
      color: #dc2626;
      background: #fef2f2;
    }

    &:disabled {
      color: #d1d5db;
      cursor: not-allowed;
    }
  }
}

// ── Minimal streaming indicator (replaces bulky thinking-bubble) ──
.loading-indicator {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 0;

  .load-dot-pulse {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #a78bfa;
    animation: load-pulse 1.4s ease-in-out infinite;
    flex-shrink: 0;
  }

  .load-label {
    font-size: 12.5px;
    color: #9ca3af;
    font-weight: 400;
  }
}

@keyframes load-pulse {
  0%, 100% { opacity: 0.3; transform: scale(0.8); }
  50%      { opacity: 1;   transform: scale(1.2); }
}

// ── Streaming answer cursor (blinking ▍ at end of text) ──
:deep(.msg-bubble.assistant.is-streaming) {
  position: relative;
  &::after {
    content: '▍';
    color: #7c3aed;
    animation: cursor-blink 0.8s step-end infinite;
    margin-left: 1px;
  }
}

@keyframes cursor-blink {
  0%, 100% { opacity: 1; }
  50%      { opacity: 0; }
}

.scroll-fab {
  position: absolute;
  bottom: 24px;
  right: 24px;
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: var(--color-surface, $surface);
  border: 1px solid var(--color-border, $border);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
  transition: transform 0.15s, box-shadow 0.15s;
  z-index: 10;

  &:hover {
    transform: scale(1.1);
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12);
  }

  .fab-icon {
    font-size: 16px;
    color: var(--color-text-secondary, $text-secondary);
    line-height: 1;
  }
}

.fab-fade-enter-active,
.fab-fade-leave-active {
  transition: opacity 0.2s, transform 0.2s;
}

.fab-fade-enter-from,
.fab-fade-leave-to {
  opacity: 0;
  transform: translateY(8px);
}

.msg-area::-webkit-scrollbar {
  width: 5px;
}

.msg-area::-webkit-scrollbar-track {
  background: transparent;
}

.msg-area::-webkit-scrollbar-thumb {
  background: transparent;
  border-radius: 3px;
  transition: background 0.3s;
}

.msg-area:hover::-webkit-scrollbar-thumb {
  background: #d1d5db;
}

.msg-area::-webkit-scrollbar-thumb:hover {
  background: #9ca3af;
}

// Collapsible tool group (consecutive tool calls)
.tool-group-details {
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  overflow: hidden;
  margin-bottom: 14px;

  &[open] {
    border-color: #d1d5db;
  }

  .tool-group-summary {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 6px 10px;
    cursor: pointer;
    user-select: none;
    font-size: 12px;
    color: #9ca3af;
    list-style: none;

    &::-webkit-details-marker {
      display: none;
    }
  }

  .tg-label {
    font-size: 11.5px;
    color: #6b7280;
  }

  .tg-chevron {
    color: #c4c8cf;
    flex-shrink: 0;
    transition: transform 0.15s;
    .tool-group-details[open] & {
      transform: rotate(180deg);
    }
  }

  .tool-group-body {
    padding: 4px 8px 6px;
    border-top: 1px solid #f3f4f6;

    :deep(.msg-row) {
      margin-bottom: 4px;
    }

    :deep(.msg-row:last-child) {
      margin-bottom: 2px;
    }
  }
}

// Canvas preview panel (chat page)
.canvas-preview-panel {
  width: 320px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  border-left: 1px solid var(--color-border, $border);
  background: #fafafa;

  .preview-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 8px 12px;
    border-bottom: 1px solid var(--color-border, $border);

    .preview-title {
      font-size: 13px;
      font-weight: 600;
      color: var(--color-text, $text);
    }

    .preview-actions {
      display: flex;
      gap: 4px;
      align-items: center;
    }
  }

  .preview-iframe {
    flex: 1;
    border: none;
    width: 100%;
  }
}

.canvas-preview-fab {
  position: fixed;
  bottom: 100px;
  right: 24px;
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  background: var(--color-surface, $surface);
  border: 1px solid var(--color-border, $border);
  border-radius: 20px;
  cursor: pointer;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
  z-index: 20;
  transition: transform 0.15s, box-shadow 0.15s;

  &:hover {
    transform: scale(1.05);
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12);
  }

  .fab-badge {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #f59e0b;
    animation: badge-pulse 2s infinite;
  }

  .fab-label {
    font-size: 12px;
    font-weight: 500;
    color: var(--color-text-secondary, $text-secondary);
  }
}

@keyframes badge-pulse {
  0%,
  100% {
    opacity: 1;
  }

  50% {
    opacity: 0.4;
  }
}

// File manager selected images preview bar
.fm-images-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  max-width: $msg-max-width;
  margin: 0 auto 4px;
  padding: 8px 14px;
  background: #eef2ff;
  border: 1px solid rgba(#4f46e5, 0.15);
  border-radius: 10px;
  flex-wrap: wrap;
  flex-shrink: 0;

  .fm-images-label {
    font-size: 12px;
    color: #6b7280;
    white-space: nowrap;
  }

  .fm-img-tag {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    background: #fff;
    border: 1px solid #d1d5db;
    border-radius: 6px;
    padding: 3px 8px 3px 4px;
    font-size: 12px;

    img {
      width: 24px;
      height: 24px;
      border-radius: 4px;
      object-fit: cover;
    }

    .fm-img-name {
      max-width: 100px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      color: #1e293b;
    }

    .fm-img-remove {
      cursor: pointer;
      color: #94a3b8;
      font-weight: 700;
      font-size: 14px;
      line-height: 1;
      margin-left: 2px;
      &:hover {
        color: #dc2626;
      }
    }
  }
}
</style>

<style lang="scss">
@use '@/assets/styles/md-body.scss' as *;
</style>
