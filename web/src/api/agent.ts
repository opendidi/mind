/**
 * Agent API — SSE streaming chat client
 */

export interface AgentEvent {
  type:
    | 'token'
    | 'thinking'
    | 'tool_call'
    | 'tool_result'
    | 'plan'
    | 'step_start'
    | 'step_end'
    | 'step_fail'
    | 'progress'
    | 'message'
    | 'trace'
    | 'error'
    | 'done'
    | 'references'
    | 'sub_agent_start'
    | 'sub_agent_token'
    | 'sub_agent_end'
  data: any
}

export interface Message {
  role: 'user' | 'assistant' | 'system'
  content: string
}

export interface AgentChatOptions {
  userMessage: string
  user_id?: string
  canvasContext?: any
  canvasSnapshot?: any[] | null
  images?: string[]
  onEvent?: (event: AgentEvent) => void
  onError?: (error: Error) => void
  onComplete?: () => void
  signal?: AbortSignal
}

const API_BASE = (import.meta.env.VITE_GLOB_API_URL as string) || '/v1'

/**
 * Send a message to the Agent and receive SSE events.
 * Returns an abort controller for cancellation.
 */
export function agentChat(options: AgentChatOptions): AbortController {
  const controller = new AbortController()
  const signal = options.signal || controller.signal

  const body = JSON.stringify({
    message: options.userMessage,
    user_id: options.user_id || 'anonymous',
    canvas_context: options.canvasContext,
    canvas_snapshot: options.canvasSnapshot || null,
    images: options.images || [],
  })

  fetch(`${API_BASE}/agent/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body,
    signal,
  })
    .then(async response => {
      if (!response.ok) {
        // Handle rate limit with retry hint
        if (response.status === 429) {
          const retryAfter = response.headers.get('Retry-After') || '60'
          throw new Error(`请求过于频繁，请 ${retryAfter} 秒后重试`)
        }
        const err = await response.text()
        throw new Error(`Agent API error: ${response.status} ${err}`)
      }

      const reader = response.body?.getReader()
      if (!reader) {
        throw new Error('No response body')
      }

      const decoder = new TextDecoder()
      let buffer = ''
      const READ_TIMEOUT_MS = 120_000 // 2 min idle timeout
      let lastReadTime = Date.now()

      while (true) {
        // Add read timeout — AbortController fires if server hangs
        if (Date.now() - lastReadTime > READ_TIMEOUT_MS) {
          options.onError?.(new Error('SSE read timeout'))
          return
        }
        const { done, value } = await reader.read()
        lastReadTime = Date.now()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const event: AgentEvent = JSON.parse(line.slice(6))
              options.onEvent?.(event)

              if (event.type === 'done') {
                options.onComplete?.()
                return
              }
            } catch {
              // Skip malformed JSON
            }
          }
        }
      }

      options.onComplete?.()
    })
    .catch(error => {
      if (error.name === 'AbortError') return
      options.onError?.(error)
    })

  return controller
}

/**
 * Request TTS audio from the backend ChatTTS endpoint.
 * Returns the audio URL to play.
 */
export async function requestTTS(text: string, signal?: AbortSignal): Promise<string> {
  const resp = await fetch(`${API_BASE}/agent/tts`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text }),
    signal,
  })

  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ error: `HTTP ${resp.status}` }))
    throw new Error(err.error || `TTS request failed (${resp.status})`)
  }

  const data = await resp.json()
  return data.audio_url as string
}
