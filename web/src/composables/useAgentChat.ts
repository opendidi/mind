/**
 * Agent Chat Composable — SSE streaming communication
 */
import { ref, type Ref } from 'vue'
import { agentChat } from '@/api/agent'

// Types
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
  references?: Array<{ title?: string; url: string }>
}

export interface UseAgentChatOptions {
  userId?: string
  onToolCall?: (name: string, args: Record<string, unknown>) => void
  onToolResult?: (name: string, args: Record<string, unknown>, success: boolean, result: unknown) => void
  onMessage?: (text: string) => void
  onError?: (message: string) => void
  onDone?: () => void
  onEvent?: (type: string, data: any) => void
}

export interface UseAgentChatReturn {
  messages: Ref<ChatMessage[]>
  loading: Ref<boolean>
  currentTool: Ref<string>
  thinkingText: Ref<string>
  send: (text: string, images?: string[], model?: string, quote?: QuoteInfo, files?: ChatFile[]) => Promise<void>
  abort: () => void
  retry: () => void
  clear: () => void
  addMessage: (role: ChatMessage['role'], text: string) => void
  addUserMessage: (text: string, images?: string[], quote?: QuoteInfo) => void
}

export function useAgentChat(options: UseAgentChatOptions = {}): UseAgentChatReturn {
  const messages = ref<ChatMessage[]>([])
  const loading = ref(false)
  const currentTool = ref('')
  const thinkingText = ref('')
  const currentThinking = ref('')

  let msgIdCounter = 0
  let abortCtrl: AbortController | null = null
  let _lastUserText = ''
  let _lastUserImages: string[] | undefined = undefined
  let _lastUserFiles: ChatFile[] | undefined = undefined
  const pendingToolArgs = new Map<string, Record<string, unknown>>()
  let pendingToolCount = 0

  function addMessage(role: ChatMessage['role'], text: string) {
    messages.value.push({
      id: `msg-${++msgIdCounter}`,
      role,
      text,
      timestamp: new Date().toLocaleTimeString(),
    })
  }

  function addUserMessage(text: string, images?: string[], quote?: QuoteInfo, files?: ChatFile[]) {
    // Strip internal markers from display text
    let displayText = text
    if (files) {
      for (const f of files) {
        const marker = `[上传文件: ${f.objectName} (${f.name})]`
        displayText = displayText.replace(marker + '\n', '').replace(marker, '')
      }
    }
    displayText = displayText.replace(/\[图片\d+:\s*\S+\]\n?/g, '').trim()
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
    return id
  }

  function updateLastToolMessage(name: string, success: boolean, result: unknown): string | undefined {
    if (pendingToolCount <= 0) return undefined
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
    pendingToolCount = 0
    pendingToolArgs.clear()
  }

  function handleSSEEvent(eventType: string, data: any) {
    switch (eventType) {
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
      case 'token': {
        const text = data.text as string
        if (!text) break
        const last = messages.value[messages.value.length - 1]
        if (last && last.role === 'agent' && last.text !== undefined) {
          last.text += text
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
          messages.value.push(newMsg)
        }
        thinkingText.value = ''
        break
      }
      case 'message': {
        const msgText = data.text as string
        const lastMsg = messages.value[messages.value.length - 1]
        if (lastMsg && lastMsg.role === 'agent' && lastMsg.text) {
          lastMsg.text = msgText || lastMsg.text
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
          messages.value.push(newMsg)
        }
        thinkingText.value = ''
        options.onMessage?.(msgText)
        break
      }
      case 'thinking':
        currentThinking.value += (data.text || '')
        thinkingText.value = data.text || ''
        break
      case 'error':
        addMessage('error', data.message)
        flushPendingTools()
        loading.value = false
        currentTool.value = ''
        thinkingText.value = ''
        currentThinking.value = ''
        options.onError?.(data.message)
        break
      case 'done':
        // Handled by onComplete callback (agentChat calls both onEvent + onComplete for 'done')
        break
      default:
        options.onEvent?.(eventType, data)
        break
    }
  }

  async function send(text: string, images?: string[], _model?: string, quote?: QuoteInfo, files?: ChatFile[]): Promise<void> {
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

    loading.value = true
    abortCtrl = agentChat({
      userMessage: apiText,
      user_id: options.userId,
      onEvent: (event) => handleSSEEvent(event.type, event.data),
      onError: (err) => {
        addMessage('error', err.message)
        loading.value = false
        options.onError?.(err.message)
      },
      onComplete: () => {
        loading.value = false
        options.onDone?.()
      },
    })
  }

  function abort() {
    abortCtrl?.abort()
    abortCtrl = null
    loading.value = false
    currentTool.value = ''
    thinkingText.value = ''
    pendingToolArgs.clear()
    pendingToolCount = 0
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
    send(_lastUserText, _lastUserImages, undefined, undefined, _lastUserFiles)
  }

  function clear() {
    abort()
    messages.value = []
    currentTool.value = ''
    thinkingText.value = ''
    msgIdCounter = 0
    pendingToolCount = 0
    pendingToolArgs.clear()
  }

  return {
    messages,
    loading,
    currentTool,
    thinkingText,
    send,
    abort,
    retry,
    clear,
    addMessage,
    addUserMessage,
  }
}
