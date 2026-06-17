/**
 * AgentStreamHandler — SSE event stream manager for agent chat.
 *
 * Manages the lifecycle of an SSE connection and dispatches
 * typed events to the AgentPanel UI components.
 */

import { reactive } from 'vue';
import { agentChat, type AgentEvent, type AgentChatOptions } from '@/api/agent';
import { useCommonStoreWithOut } from '@/store/modules/common';

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

export interface ToolCallRecord {
  id: string;
  tool: string;
  args: any;
  success?: boolean;
  result?: any;
  status: 'pending' | 'running' | 'success' | 'error';
  timestamp: number;
}

export interface PlanInfo {
  goal: string;
  nodes: PlanNode[];
  risk: string;
  mode: string;
}

export interface PlanNode {
  id: string;
  desc: string;
  depends_on: string[];
  parallel_group?: string;
  confirm?: boolean;
  status?: 'pending' | 'running' | 'completed' | 'failed';
}

let _msgId = 0;
function nextId(): string {
  return `msg_${++_msgId}_${Date.now()}`;
}

export class AgentStreamHandler {
  private controller: AbortController | null = null;
  private currentAssistantMsg: ChatMessage | null = null;

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
  private _onToolResult: ((tool: string, args: Record<string, unknown>, success: boolean, result: unknown) => void) | null = null;

  onChange(fn: (state: StreamState) => void) {
    this.listeners.push(fn);
    return () => {
      this.listeners = this.listeners.filter((l) => l !== fn);
    };
  }

  onToolResult(fn: (tool: string, args: Record<string, unknown>, success: boolean, result: unknown) => void) {
    this._onToolResult = fn;
  }

  private notify() {
    this.listeners.forEach((fn) => fn({ ...this.state }));
  }

  send(userMessage: string, options?: Partial<AgentChatOptions>) {
    // Abort previous request
    this.abort();

    // Add user message
    const userMsg: ChatMessage = {
      id: nextId(),
      role: 'user',
      content: userMessage,
      timestamp: Date.now(),
    };
    this.state.messages.push(userMsg);

    // Reset state
    this.state.connected = true;
    this.state.loading = true;
    this.state.error = null;
    this.state.toolCalls = [];
    this.state.plan = null;
    this.currentAssistantMsg = null;

    this.notify();

    // Build canvas context from Pinia common store
    let canvasContext = undefined;
    try {
      const commonStore = useCommonStoreWithOut();
      const topology = commonStore.topology as any;
      if (topology && typeof topology.data === 'function') {
        const data = topology.data();
        const pens = data?.pens || [];
        canvasContext = {
          pens: pens.map((p: any) => ({
            id: p.id || p.penId,
            type: p.type || 'rectangle',
            text: p.text || '',
            x: p.x || 0, y: p.y || 0,
            width: p.width || 100, height: p.height || 60,
          })),
          lines: data?.lines || [],
        };
      }
    } catch { /* ignore — canvas context is optional */ }

    this.controller = agentChat({
      userMessage,
      canvasContext,
      user_id: options?.user_id,
      signal: options?.signal,
      onEvent: (event) => this.handleEvent(event),
      onError: (error) => {
        this.state.loading = false;
        this.state.error = error.message;
        this.state.connected = false;
        this.notify();
      },
      onComplete: () => {
        this.state.loading = false;
        this.state.connected = false;
        this.notify();
      },
    });
  }

  private handleEvent(event: AgentEvent) {
    switch (event.type) {
      case 'token': {
        if (!this.currentAssistantMsg) {
          this.currentAssistantMsg = {
            id: nextId(),
            role: 'assistant',
            content: '',
            timestamp: Date.now(),
          };
          this.state.messages.push(this.currentAssistantMsg);
        }
        this.currentAssistantMsg.content += event.data?.text || '';
        break;
      }

      case 'thinking': {
        if (!this.currentAssistantMsg) {
          this.currentAssistantMsg = {
            id: nextId(),
            role: 'assistant',
            content: '',
            timestamp: Date.now(),
          };
          this.state.messages.push(this.currentAssistantMsg);
        }
        this.currentAssistantMsg.thinking = (this.currentAssistantMsg.thinking || '') + (event.data?.content || '');
        break;
      }

      case 'tool_call': {
        const record: ToolCallRecord = {
          id: `tool_${Date.now()}`,
          tool: event.data?.tool || '',
          args: event.data?.args || {},
          status: 'running',
          timestamp: Date.now(),
        };
        this.state.toolCalls.push(record);

        if (!this.currentAssistantMsg) {
          this.currentAssistantMsg = {
            id: nextId(),
            role: 'assistant',
            content: '',
            timestamp: Date.now(),
          };
          this.state.messages.push(this.currentAssistantMsg);
        }
        if (!this.currentAssistantMsg.toolCalls) {
          this.currentAssistantMsg.toolCalls = [];
        }
        this.currentAssistantMsg.toolCalls.push(record);
        break;
      }

      case 'tool_result': {
        const toolName = event.data?.tool;
        const success = event.data?.success;
        const result = event.data?.result;
        // Update last matching pending tool call
        let matchedArgs: Record<string, unknown> = {};
        for (let i = this.state.toolCalls.length - 1; i >= 0; i--) {
          if (this.state.toolCalls[i].tool === toolName && this.state.toolCalls[i].status === 'running') {
            this.state.toolCalls[i].status = success ? 'success' : 'error';
            this.state.toolCalls[i].success = success;
            this.state.toolCalls[i].result = result;
            matchedArgs = this.state.toolCalls[i].args as Record<string, unknown>;
            break;
          }
        }
        // Also update in current message
        if (this.currentAssistantMsg?.toolCalls) {
          for (let i = this.currentAssistantMsg.toolCalls.length - 1; i >= 0; i--) {
            if (this.currentAssistantMsg.toolCalls[i].tool === toolName && this.currentAssistantMsg.toolCalls[i].status === 'running') {
              this.currentAssistantMsg.toolCalls[i].status = success ? 'success' : 'error';
              this.currentAssistantMsg.toolCalls[i].success = success;
              this.currentAssistantMsg.toolCalls[i].result = result;
              break;
            }
          }
        }
        // Bridge to canvas execution
        this._onToolResult?.(toolName, matchedArgs, success, result);
        break;
      }

      case 'plan': {
        const data = event.data || {};
        this.state.plan = {
          goal: data.goal || '',
          nodes: (data.nodes || []).map((n: any) => ({
            ...n,
            status: 'pending' as const,
          })),
          risk: data.risk || 'low',
          mode: data.mode || 'simple',
        };
        break;
      }

      case 'step_start': {
        if (this.state.plan) {
          const node = this.state.plan.nodes.find((n) => n.id === event.data?.step_id);
          if (node) node.status = 'running';
        }
        break;
      }

      case 'step_end': {
        if (this.state.plan) {
          const node = this.state.plan.nodes.find((n) => n.id === event.data?.step_id);
          if (node) node.status = 'completed';
        }
        break;
      }

      case 'step_fail': {
        if (this.state.plan) {
          const node = this.state.plan.nodes.find((n) => n.id === event.data?.step_id);
          if (node) node.status = 'failed';
        }
        break;
      }

      case 'message': {
        if (!this.currentAssistantMsg) {
          this.currentAssistantMsg = {
            id: nextId(),
            role: 'assistant',
            content: event.data?.text || '',
            timestamp: Date.now(),
          };
          this.state.messages.push(this.currentAssistantMsg);
        }
        break;
      }

      case 'error': {
        this.state.error = event.data?.message || '未知错误';
        break;
      }

      case 'trace': {
        this.state.traceId = event.data?.trace_id || null;
        break;
      }

      case 'progress': {
        // Progress updates can be shown as system messages
        break;
      }
    }

    this.notify();
  }

  abort() {
    this.controller?.abort();
    this.controller = null;
    this.state.loading = false;
    this.state.connected = false;
  }

  clear() {
    this.abort();
    Object.assign(this.state, {
      connected: false,
      loading: false,
      error: null,
      messages: [],
      toolCalls: [],
      plan: null,
      traceId: null,
    });
    this.currentAssistantMsg = null;
    this.notify();
  }
}
