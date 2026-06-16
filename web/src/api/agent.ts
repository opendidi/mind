/**
 * Agent API — SSE streaming chat client
 */

export interface AgentEvent {
  type: 'token' | 'thinking' | 'tool_call' | 'tool_result' | 'plan'
    | 'step_start' | 'step_end' | 'step_fail' | 'progress'
    | 'message' | 'trace' | 'error' | 'done';
  data: any;
}

export interface Message {
  role: 'user' | 'assistant' | 'system';
  content: string;
}

export interface AgentChatOptions {
  userMessage: string;
  user_id?: string;
  canvasContext?: any;
  onEvent?: (event: AgentEvent) => void;
  onError?: (error: Error) => void;
  onComplete?: () => void;
  signal?: AbortSignal;
}

const API_BASE = import.meta.env.VITE_API_URL || '/v1';

/**
 * Send a message to the Agent and receive SSE events.
 * Returns an abort controller for cancellation.
 */
export function agentChat(options: AgentChatOptions): AbortController {
  const controller = new AbortController();
  const signal = options.signal || controller.signal;

  const body = JSON.stringify({
    message: options.userMessage,
    user_id: options.user_id || 'anonymous',
    canvas_context: options.canvasContext,
  });

  fetch(`${API_BASE}/agent/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body,
    signal,
  })
    .then(async (response) => {
      if (!response.ok) {
        const err = await response.text();
        throw new Error(`Agent API error: ${response.status} ${err}`);
      }

      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error('No response body');
      }

      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const event: AgentEvent = JSON.parse(line.slice(6));
              options.onEvent?.(event);

              if (event.type === 'done') {
                options.onComplete?.();
                return;
              }
            } catch {
              // Skip malformed JSON
            }
          }
        }
      }

      options.onComplete?.();
    })
    .catch((error) => {
      if (error.name === 'AbortError') return;
      options.onError?.(error);
    });

  return controller;
}
