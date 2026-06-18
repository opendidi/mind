/**
 * AgentStreamHandler — thin wrapper around useAgentChat for the AgentPanel drawer.
 *
 * Maintains backward compatibility with AgentPanel's StreamState / ChatMessage model.
 * All SSE event handling is delegated to the unified useAgentChat composable.
 */
import { reactive, watch } from 'vue';
import { useAgentChat, type PlanInfo, type ToolCallRecord } from '@/composables/useAgentChat';

export type { PlanInfo, ToolCallRecord };

export interface StreamState {
  connected: boolean;
  loading: boolean;
  error: string | null;
  messages: ChatMessage[];
  toolCalls: ToolCallRecord[];
  plan: PlanInfo | null;
  traceId: string | null;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  thinking?: string;
  toolCalls?: ToolCallRecord[];
  timestamp: number;
}

let _msgId = 0;
function nextId(): string {
  return `msg_${++_msgId}_${Date.now()}`;
}

export class AgentStreamHandler {
  private chat: ReturnType<typeof useAgentChat>;
  private currentAssistantMsg: ChatMessage | null = null;
  private currentAssistantTools: ToolCallRecord[] = [];
  private _onToolResult: ((tool: string, args: Record<string, unknown>, success: boolean, result: unknown) => void) | null = null;

  state = reactive<StreamState>({
    connected: false,
    loading: false,
    error: null,
    messages: [],
    toolCalls: [],
    plan: null,
    traceId: null,
  });

  private listeners: Array<(state: StreamState) => void> = [];

  constructor() {
    this.chat = useAgentChat({
      onToolResult: (tool, args, success, result) => {
        this._onToolResult?.(tool, args, success, result);
      },
      onError: (msg) => {
        this.state.error = msg;
        this.notify();
      },
      onDone: () => {
        this.notify();
      },
    });

    // Sync composable state → StreamState
    watch(
      () => ({
        loading: this.chat.loading.value,
        connected: this.chat.connected.value,
        plan: this.chat.plan.value,
        traceId: this.chat.traceId.value,
        toolCalls: this.chat.toolCalls.value,
        messages: this.chat.messages.value,
      }),
      (s) => {
        // Sync simple fields
        this.state.loading = s.loading;
        this.state.connected = s.connected;
        this.state.plan = s.plan;
        this.state.traceId = s.traceId;
        this.state.toolCalls = s.toolCalls;
        this.state.error = null; // cleared on next send

        // Map composable messages to AgentPanel message format
        this.state.messages = this.mapMessages(s.messages);
        this.notify();
      },
      { deep: true }
    );
  }

  private mapMessages(msgs: import('@/composables/useAgentChat').ChatMessage[]): ChatMessage[] {
    const result: ChatMessage[] = [];
    let currentAssistant: ChatMessage | null = null;

    for (const m of msgs) {
      switch (m.role) {
        case 'user':
          result.push({
            id: m.id,
            role: 'user',
            content: m.text || '',
            timestamp: Date.now(),
          });
          break;

        case 'agent':
          currentAssistant = {
            id: m.id,
            role: 'assistant',
            content: m.text || '',
            thinking: m.thinking,
            timestamp: Date.now(),
          };
          result.push(currentAssistant);
          break;

        case 'tool': {
          const tc: ToolCallRecord = {
            id: m.id,
            tool: m.tool?.name || '',
            args: m.tool?.args || {},
            success: m.tool?.success,
            result: m.tool?.result,
            status: m.tool?.success === undefined ? 'running' : m.tool?.success ? 'success' : 'error',
            timestamp: Date.now(),
          };
          if (!currentAssistant) {
            currentAssistant = {
              id: m.id,
              role: 'assistant',
              content: '',
              timestamp: Date.now(),
            };
            result.push(currentAssistant);
          }
          if (!currentAssistant.toolCalls) currentAssistant.toolCalls = [];
          currentAssistant.toolCalls.push(tc);
          break;
        }

        case 'error':
          result.push({
            id: m.id,
            role: 'system',
            content: m.text || '未知错误',
            timestamp: Date.now(),
          });
          break;
      }
    }
    return result;
  }

  private notify() {
    this.listeners.forEach(fn => fn({ ...this.state }));
  }

  onChange(fn: (state: StreamState) => void) {
    this.listeners.push(fn);
    return () => {
      this.listeners = this.listeners.filter(l => l !== fn);
    };
  }

  onToolResult(fn: (tool: string, args: Record<string, unknown>, success: boolean, result: unknown) => void) {
    this._onToolResult = fn;
  }

  send(userMessage: string) {
    // Preserve conversation history — only reset transient state
    this.state.error = null;
    this.state.toolCalls = [];
    this.state.plan = null;
    this.currentAssistantMsg = null;
    this.currentAssistantTools = [];
    this.chat.send(userMessage);
  }

  abort() {
    this.chat.abort();
  }

  clear() {
    this.chat.clear();
    this.state.messages = [];
    this.state.toolCalls = [];
    this.state.plan = null;
    this.state.traceId = null;
    this.state.error = null;
    this.currentAssistantMsg = null;
    this.currentAssistantTools = [];
    this.notify();
  }
}
