/**
 * useAgentChat — Unified Agent chat composable (SSE streaming).
 *
 * Used by both the full-page chat view (/chat/:id?) and the
 * in-canvas AgentPanel drawer. All SSE event handling is centralized here.
 */
import { ref, type Ref, type ComputedRef, computed } from 'vue'
import { agentChat } from '@/api/agent'
import { useCommonStoreWithOut } from '@/store/modules/common'
import { useSelection } from '@/services/selections'

// ── Types ──────────────────────────────────────────────────────────

export interface ToolInfo {
  name: string
  args: Record<string, unknown>
  success?: boolean
  result?: unknown
}

export interface QuoteInfo {
  text: string
  msgId: string
  role: 'user' | 'agent'
}

export interface ChatFile {
  name: string
  objectName: string
  url: string
}

export interface ChatMessage {
  id: string
  role: 'user' | 'agent' | 'tool' | 'error'
  text?: string
  images?: string[]
  files?: ChatFile[]
  quote?: QuoteInfo
  tool?: ToolInfo
  thinking?: string
  timestamp?: string
  feedback?: 'liked' | 'disliked'
  references?: Array<{ title?: string; url: string; snippet?: string; domain?: string }>
}

export interface ToolCallRecord {
  id: string
  tool: string
  args: Record<string, unknown>
  success?: boolean
  result?: unknown
  status: 'pending' | 'running' | 'success' | 'error'
  timestamp: number
}

export interface PlanNode {
  id: string
  desc: string
  depends_on: string[]
  parallel_group?: string
  confirm?: boolean
  status?: 'pending' | 'running' | 'completed' | 'failed'
}

export interface PlanInfo {
  goal: string
  nodes: PlanNode[]
  risk: string
  mode: string
}

export interface UseAgentChatOptions {
  userId?: string
  /** Optional canvas context override (defaults to reading from Meta2D + selection) */
  getCanvasContext?: () => CanvasContext | null
  onToolCall?: (name: string, args: Record<string, unknown>) => void
  onToolResult?: (name: string, args: Record<string, unknown>, success: boolean, result: unknown) => void
  onMessage?: (text: string) => void
  onError?: (message: string) => void
  onDone?: () => void
  onEvent?: (type: string, data: any) => void
  /** Called periodically during streaming — hook for auto-save */
  onStreamTick?: () => void
}

export interface CanvasContext {
  pens: any[]
  lines: any[]
  selectedIds: string[]
  canvasInfo: { width: number; height: number }
  viewportCenter: { x: number; y: number }
}

export interface UseAgentChatReturn {
  messages: Ref<ChatMessage[]>
  loading: Ref<boolean>
  connected: Ref<boolean>
  currentTool: Ref<string>
  thinkingText: Ref<string>
  plan: Ref<PlanInfo | null>
  toolCalls: Ref<ToolCallRecord[]>
  traceId: Ref<string | null>
  streamDisconnected: Ref<boolean>
  send: (text: string, images?: string[], model?: string, quote?: QuoteInfo, files?: ChatFile[]) => Promise<void>
  abort: () => void
  retry: () => void
  clear: () => void
  addMessage: (role: ChatMessage['role'], text: string) => void
  addUserMessage: (text: string, images?: string[], quote?: QuoteInfo) => void
  /** Force-save current streamed content (called on unmount) */
  flushStreamSave: () => void
}

// ── Default canvas context builder ─────────────────────────────────

export function buildCanvasContext(): CanvasContext | null {
  try {
    const meta2d = (window as any).meta2d
    if (!meta2d || typeof meta2d.data !== 'function') return null

    const data = meta2d.data()
    if (!data) return null

    const { selections } = useSelection()
    const selectedPen = selections.pen

    // If user has a pen selected, prioritize its neighborhood
    const pens: any[] = []
    if (selectedPen) {
      pens.push({
        id: selectedPen.id,
        type: selectedPen.name || 'rectangle',
        text: selectedPen.text || '',
        x: selectedPen.x || 0, y: selectedPen.y || 0,
        width: selectedPen.width || 100, height: selectedPen.height || 60,
      })
    }

    // Include all pens (trimmed for large diagrams)
    const MAX_PENS = 50
    const allPens = (data.pens || []).slice(0, MAX_PENS)
    for (const p of allPens) {
      if (!pens.find(x => x.id === p.id)) {
        pens.push({
          id: p.id || p.penId,
          type: p.name || p.type || 'rectangle',
          text: (p.text || '').slice(0, 200),
          x: p.x || 0, y: p.y || 0,
          width: p.width || 100, height: p.height || 60,
        })
      }
    }

    // Include line data (was always empty before!)
    const lines = (data.lines || []).map((l: any) => ({
      from: l.fromPen || l.from,
      to: l.toPen || l.to,
      text: (l.text || '').slice(0, 200),
    }))

    // Viewport center in canvas coordinates — for placing new elements in view
    const scale = meta2d.store?.data?.scale || 1
    const scrollX = meta2d.canvas?.scroll?.scrollX || 0
    const scrollY = meta2d.canvas?.scroll?.scrollY || 0
    const vw = meta2d.canvas?.parentElement?.clientWidth || 1200
    const vh = meta2d.canvas?.parentElement?.clientHeight || 800
    const viewportCenter = {
      x: Math.round((-scrollX + vw / 2) / scale),
      y: Math.round((-scrollY + vh / 2) / scale),
    }

    return {
      pens,
      lines,
      selectedIds: selectedPen ? [selectedPen.id] : [],
      canvasInfo: {
        width: data.width || 1920,
        height: data.height || 1080,
      },
      viewportCenter,
    }
  } catch {
    return null
  }
}

// ── Composable ─────────────────────────────────────────────────────

export function useAgentChat(options: UseAgentChatOptions = {}): UseAgentChatReturn {
  const messages = ref<ChatMessage[]>([])
  const loading = ref(false)
  const connected = ref(false)
  const streamDisconnected = ref(false)
  const currentTool = ref('')
  const thinkingText = ref('')
  const currentThinking = ref('')
  const plan = ref<PlanInfo | null>(null)
  const toolCalls = ref<ToolCallRecord[]>([])
  const traceId = ref<string | null>(null)

  let msgIdCounter = 0
  let abortCtrl: AbortController | null = null
  let _lastUserText = ''
  let _lastUserImages: string[] | undefined = undefined
  let _lastUserFiles: ChatFile[] | undefined = undefined
  const pendingToolArgs = new Map<string, Record<string, unknown>>()
  let pendingToolCount = 0
  let pendingRefs: Array<{ title?: string; url: string; snippet?: string; domain?: string }> | null = null

  // ── Stream auto-save ──────────────────────────────────────────────
  let _streamTokenCount = 0
  let _streamSaveInterval: ReturnType<typeof setInterval> | null = null

  function _tickStreamSave() {
    if (_streamTokenCount > 0) {
      _streamTokenCount = 0
      options.onStreamTick?.()
    }
  }

  function flushStreamSave() {
    _tickStreamSave()
  }

  function _startStreamSave() {
    _streamTokenCount = 0
    if (_streamSaveInterval) clearInterval(_streamSaveInterval)
    _streamSaveInterval = setInterval(_tickStreamSave, 3000)
  }

  function _stopStreamSave() {
    if (_streamSaveInterval) {
      clearInterval(_streamSaveInterval)
      _streamSaveInterval = null
    }
    _tickStreamSave()  // final save
  }

  function addMessage(role: ChatMessage['role'], text: string) {
    messages.value.push({
      id: `msg-${++msgIdCounter}`,
      role,
      text,
      timestamp: new Date().toLocaleTimeString(),
    })
  }

  function addUserMessage(text: string, images?: string[], quote?: QuoteInfo, files?: ChatFile[]) {
    let displayText = text
    // Strip file upload markers from display text (backend uses them for tool routing)
    if (files) {
      for (const f of files) {
        const marker = `[上传文件: ${f.objectName} (${f.name})]`
        displayText = displayText.replace(marker + '\n', '').replace(marker, '')
      }
    }
    messages.value.push({
      id: `msg-${++msgIdCounter}`,
      role: 'user',
      text: displayText,
      ...(images && images.length > 0 ? { images } : {}),
      ...(files && files.length > 0 ? { files } : {}),
      ...(quote ? { quote } : {}),
      timestamp: new Date().toLocaleTimeString(),
    })
  }

  function addToolMessage(name: string, args: Record<string, unknown>): string {
    const id = `msg-${++msgIdCounter}`
    pendingToolCount++
    pendingToolArgs.set(id, args)
    messages.value.push({
      id,
      role: 'tool',
      tool: { name, args },
      timestamp: new Date().toLocaleTimeString(),
    })

    toolCalls.value.push({
      id,
      tool: name,
      args,
      status: 'running',
      timestamp: Date.now(),
    })
    return id
  }

  function updateLastToolMessage(name: string, success: boolean, result: unknown): string | undefined {
    if (pendingToolCount <= 0) return undefined

    // Update in toolCalls array
    for (let i = toolCalls.value.length - 1; i >= 0; i--) {
      if (toolCalls.value[i].tool === name && toolCalls.value[i].status === 'running') {
        toolCalls.value[i].status = success ? 'success' : 'error'
        toolCalls.value[i].success = success
        toolCalls.value[i].result = result
        break
      }
    }

    // Update in messages
    for (let i = messages.value.length - 1; i >= 0; i--) {
      const m = messages.value[i]
      if (m.role === 'tool' && m.tool && m.tool.success === undefined && m.tool.name === name) {
        m.tool.success = success
        m.tool.result = result
        pendingToolCount--
        pendingToolArgs.delete(m.id)
        return m.id
      }
    }
    for (let i = messages.value.length - 1; i >= 0; i--) {
      const m = messages.value[i]
      if (m.role === 'tool' && m.tool && m.tool.success === undefined) {
        m.tool.success = success
        m.tool.result = result
        pendingToolCount--
        pendingToolArgs.delete(m.id)
        return m.id
      }
    }
    return undefined
  }

  function flushPendingTools() {
    if (pendingToolCount <= 0) return
    for (const m of messages.value) {
      if (m.role === 'tool' && m.tool && m.tool.success === undefined) {
        m.tool.success = false
        m.tool.result = '连接中断，工具可能未完成'
      }
    }
    for (const tc of toolCalls.value) {
      if (tc.status === 'running') {
        tc.status = 'error'
        tc.success = false
        tc.result = '连接中断'
      }
    }
    pendingToolCount = 0
    pendingToolArgs.clear()
  }

  function handleSSEEvent(eventType: string, data: any) {
    switch (eventType) {
      // ── Text streaming ──
      case 'token': {
        const text = data.text as string
        if (!text) break
        const last = messages.value[messages.value.length - 1]
        if (last && last.role === 'agent' && last.text !== undefined) {
          last.text += text
          // Merge any pending refs from later tool calls (e.g. 2nd web_search)
          if (pendingRefs) {
            const existing = (last.references || []) as any[]
            const seen = new Set(existing.map((r: any) => r.url))
            const newRefs = pendingRefs.filter(r => !seen.has(r.url))
            if (newRefs.length > 0) {
              last.references = [...existing, ...newRefs]
            }
            pendingRefs = null
          }
        } else {
          const newMsg: ChatMessage = {
            id: `msg-${++msgIdCounter}`,
            role: 'agent',
            text,
            timestamp: new Date().toLocaleTimeString(),
          }
          if (currentThinking.value.trim()) {
            newMsg.thinking = currentThinking.value.trim()
            currentThinking.value = ''
          }
          if (pendingRefs) {
            newMsg.references = pendingRefs
            pendingRefs = null
          }
          messages.value.push(newMsg)
        }
        thinkingText.value = ''
        // Auto-save every 10 tokens during streaming
        _streamTokenCount++
        if (_streamTokenCount >= 10) {
          _streamTokenCount = 0
          options.onStreamTick?.()
        }
        break
      }

      case 'message': {
        const msgText = data.text as string
        const lastMsg = messages.value[messages.value.length - 1]
        if (lastMsg && lastMsg.role === 'agent' && lastMsg.text) {
          lastMsg.text = msgText || lastMsg.text
          // Merge any pending refs (from later tool calls in the same turn)
          if (pendingRefs) {
            const existing = (lastMsg.references || []) as any[]
            const seen = new Set(existing.map((r: any) => r.url))
            const newRefs = pendingRefs.filter(r => !seen.has(r.url))
            if (newRefs.length > 0) {
              lastMsg.references = [...existing, ...newRefs]
            }
            pendingRefs = null
          }
        } else {
          const newMsg: ChatMessage = {
            id: `msg-${++msgIdCounter}`,
            role: 'agent',
            text: msgText,
            timestamp: new Date().toLocaleTimeString(),
          }
          if (currentThinking.value.trim()) {
            newMsg.thinking = currentThinking.value.trim()
            currentThinking.value = ''
          }
          if (pendingRefs) {
            newMsg.references = pendingRefs
            pendingRefs = null
          }
          messages.value.push(newMsg)
        }
        thinkingText.value = ''
        options.onMessage?.(msgText)
        break
      }

      // ── Thinking ──
      case 'thinking':
        currentThinking.value += (data.text || data.content || '')
        thinkingText.value = data.text || data.content || ''
        break

      // ── Tool calls ──
      case 'tool_call': {
        const name = data.tool as string
        const args = { ...data.args } as Record<string, unknown>
        addToolMessage(name, args)
        currentTool.value = name
        options.onToolCall?.(name, args)
        break
      }

      case 'tool_result': {
        const name = data.tool as string
        const msgId = updateLastToolMessage(name, data.success, data.result)
        const args = msgId ? (pendingToolArgs.get(msgId) ?? {}) : {}
        currentTool.value = ''
        options.onToolResult?.(name, args, data.success, data.result)
        break
      }

      // ── Plan / Steps ──
      case 'plan': {
        const d = data || {}
        const rawNodes = d.nodes || d.steps || []
        plan.value = {
          goal: d.goal || '',
          nodes: rawNodes.map((n: any) => ({
            id: n.id || '',
            desc: n.desc || n.description || '',
            depends_on: n.depends_on || [],
            parallel_group: n.parallel_group || undefined,
            confirm: n.confirm ?? false,
            status: 'pending' as const,
          })),
          risk: d.risk || 'low',
          mode: d.mode || 'simple',
        }
        break
      }

      case 'step_start': {
        if (plan.value) {
          const node = plan.value.nodes.find(n => n.id === (data.step_id || data.id))
          if (node) node.status = 'running'
        }
        break
      }

      case 'step_end': {
        if (plan.value) {
          const node = plan.value.nodes.find(n => n.id === (data.step_id || data.id))
          if (node) node.status = 'completed'
        }
        break
      }

      case 'step_fail': {
        if (plan.value) {
          const node = plan.value.nodes.find(n => n.id === (data.step_id || data.id))
          if (node) node.status = 'failed'
        }
        break
      }

      // ── Trace ──
      case 'trace':
        traceId.value = data.trace_id || data.traceId || null
        break

      // ── Progress ──
      case 'progress':
        // Hook for UI-level progress indicators
        break

      // ── Error ──
      case 'error':
        addMessage('error', data.message)
        flushPendingTools()
        pendingRefs = null
        loading.value = false
        connected.value = false
        currentTool.value = ''
        thinkingText.value = ''
        currentThinking.value = ''
        plan.value = null
        options.onError?.(data.message)
        break

      // ── References (web_search / web_fetch citations) ──
      // Buffer references — they arrive before the agent message, so we attach
      // them when the next agent message (token/message) is created.
      // Multiple web_search calls within one turn → MERGE refs, don't overwrite.
      case 'references': {
        const refs = (data.references || data.refs || []) as Array<{ title?: string; url: string; snippet?: string; domain?: string }>
        if (refs.length > 0) {
          // Try the last message: if it's an agent msg from THIS turn, merge refs
          const last = messages.value[messages.value.length - 1]
          if (last && last.role === 'agent') {
            const existing = (last.references || []) as any[]
            // Dedup by URL
            const seen = new Set(existing.map((r: any) => r.url))
            const newRefs = refs.filter(r => !seen.has(r.url))
            if (newRefs.length > 0) {
              last.references = [...existing, ...newRefs]
            }
          } else {
            // No agent message yet — accumulate in buffer
            if (pendingRefs) {
              const seen = new Set(pendingRefs.map(r => r.url))
              pendingRefs = [...pendingRefs, ...refs.filter(r => !seen.has(r.url))]
            } else {
              pendingRefs = refs
            }
          }
        }
        break
      }

      // ── Sub-agent events (dispatch_agent relay) ──
      case 'sub_agent_start': {
        const agent = data.agent || 'agent'
        thinkingText.value = `调用 ${agent} 中…`
        break
      }

      case 'sub_agent_token': {
        // Accumulate sub-agent output into thinking display
        const snippet = (data.text || '').slice(0, 60)
        thinkingText.value = snippet ? `[${data.agent || 'agent'}] ${snippet}` : thinkingText.value
        break
      }

      case 'sub_agent_end':
        thinkingText.value = ''
        break

      // ── Done (handled in onComplete) ──
      case 'done':
        pendingRefs = null
        break

      // ── Passthrough ──
      default:
        options.onEvent?.(eventType, data)
        break
    }
  }

  async function send(
    text: string,
    images?: string[],
    _model?: string,
    quote?: QuoteInfo,
    files?: ChatFile[],
  ): Promise<void> {
    const hasImages = images && images.length > 0
    const hasFiles = files && files.length > 0
    if ((!text.trim() && !quote && !hasImages && !hasFiles) || loading.value) return

    _lastUserText = text.trim()
    _lastUserImages = images
    _lastUserFiles = files

    addUserMessage(text.trim(), images, quote, files)

    const apiText = quote
      ? `> **${quote.role === 'user' ? '用户' : 'AI'}**：${quote.text}\n\n${text.trim()}`
      : text.trim()

    // Build canvas context (caller override or default)
    const canvasContext = options.getCanvasContext
      ? options.getCanvasContext()
      : buildCanvasContext()

    loading.value = true
    connected.value = true
    streamDisconnected.value = false
    plan.value = null
    toolCalls.value = []
    traceId.value = null
    pendingRefs = null
    _startStreamSave()

    abortCtrl = agentChat({
      userMessage: apiText,
      user_id: options.userId,
      canvasContext,
      images: images || undefined,
      onEvent: (event) => handleSSEEvent(event.type, event.data),
      onError: (err) => {
        _stopStreamSave()
        addMessage('error', err.message)
        loading.value = false
        connected.value = false
        streamDisconnected.value = true
        options.onError?.(err.message)
      },
      onComplete: () => {
        _stopStreamSave()
        loading.value = false
        connected.value = false
        options.onDone?.()
      },
    })
  }

  function abort() {
    _stopStreamSave()
    abortCtrl?.abort()
    abortCtrl = null
    loading.value = false
    connected.value = false
    streamDisconnected.value = false
    currentTool.value = ''
    thinkingText.value = ''
    pendingToolArgs.clear()
    pendingToolCount = 0
    pendingRefs = null
  }

  function retry() {
    if (!_lastUserText && !_lastUserImages?.length && !_lastUserFiles?.length) return
    abort()
    const msgs = messages.value
    let cutIdx = -1
    for (let i = msgs.length - 1; i >= 0; i--) {
      if (msgs[i].role === 'error') { cutIdx = i; break }
    }
    if (cutIdx >= 0) {
      if (cutIdx > 0 && msgs[cutIdx - 1].role === 'user') cutIdx--
      messages.value = msgs.slice(0, cutIdx)
    }
    streamDisconnected.value = false
    send(_lastUserText, _lastUserImages, undefined, undefined, _lastUserFiles)
  }

  function clear() {
    _stopStreamSave()
    abort()
    messages.value = []
    toolCalls.value = []
    plan.value = null
    currentTool.value = ''
    thinkingText.value = ''
    traceId.value = null
    streamDisconnected.value = false
    msgIdCounter = 0
    pendingToolCount = 0
    pendingToolArgs.clear()
  }

  return {
    messages,
    loading,
    connected,
    currentTool,
    thinkingText,
    plan,
    toolCalls,
    traceId,
    streamDisconnected,
    send,
    abort,
    retry,
    clear,
    addMessage,
    addUserMessage,
    flushStreamSave,
  }
}
