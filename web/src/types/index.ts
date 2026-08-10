// -*- coding: UTF-8 -*-
/**
 * Shared TypeScript type definitions for the Mind project.
 *
 * Centralizes types that were previously scattered as `any` annotations
 * across canvasBridge.ts, useAgentChat.ts, api/*.ts, and related files.
 *
 * Usage:
 *   import type { Pen, Line, CanvasSnapshot, SSEEvent, ... } from '@/types';
 */

// ── Canvas / Meta2D Types ──────────────────────────────────────────────

/** A single pen (graphics object) on the Meta2D canvas. */
export interface Pen {
  id: string;
  name: string;
  type: string;
  x: number;
  y: number;
  width: number;
  height: number;
  text?: string;
  tags?: string[];
  [key: string]: unknown;
}

/** A connection line between two pens on the canvas. */
export interface Line {
  id: string;
  name: string;
  from: string;
  to: string;
  fromArrow?: string;
  toArrow?: string;
  [key: string]: unknown;
}

/** Full canvas state snapshot sent to the agent. */
export interface CanvasSnapshot {
  pens: Pen[];
  lines: Line[];
  version?: number;
}

/** Meta2D store reference (minimal interface for canvas operations). */
export interface Meta2DStore {
  data: {
    pens: Pen[];
    lines: Line[];
  };
  getPen(id: string): Pen | undefined;
  getLine(id: string): Line | undefined;
  [key: string]: unknown;
}

// ── Chat / Agent SSE Event Types ───────────────────────────────────────

/** SSE event from the agent chat stream. */
export interface SSEEvent {
  type: 'token' | 'tool_call' | 'tool_result' | 'llm_response' | 'error' | 'done' | 'sub_agent_start' | 'sub_agent_end';
  data: unknown;
}

/** Tool call event payload. */
export interface ToolCallEvent {
  name: string;
  args: Record<string, unknown>;
  id?: string;
}

/** Tool result event payload. */
export interface ToolResultEvent {
  tool_name: string;
  success: boolean;
  result: Record<string, unknown>;
  node_id?: string;
}

/** Agent chat message (conversation history item). */
export interface AgentMessage {
  role: 'user' | 'assistant' | 'system' | 'tool';
  content: string;
  tool_calls?: ToolCall[];
  tool_call_id?: string;
}

/** A single tool call within an assistant message. */
export interface ToolCall {
  id: string;
  type: 'function';
  function: {
    name: string;
    arguments: string;
  };
}

// ── API Response Types ─────────────────────────────────────────────────

/** Standard API response envelope. */
export interface ApiResponse<T = unknown> {
  code: number;
  message: string;
  data: T;
}

/** Paginated list response. */
export interface PaginatedResponse<T = unknown> {
  code: number;
  message: string;
  data: {
    records: T[];
    total: number;
    current: number;
    pageSize: number;
  };
}

/** Material / file item. */
export interface MaterialItem {
  id: number;
  name: string;
  type: string;
  size: number;
  url: string;
  folder: string;
  parentId: number;
  userId: string;
  createdAt: string;
  updatedAt: string;
}

/** Blueprint item. */
export interface BlueprintItem {
  id: number;
  name: string;
  data: Record<string, unknown>;
  userId: string;
  createdAt: string;
  updatedAt: string;
}

/** Chat conversation. */
export interface Conversation {
  id: string;
  title: string;
  messages: AgentMessage[];
  createdAt: string;
  updatedAt: string;
}

// ── File Manager Types ─────────────────────────────────────────────────

/** A node in the file manager tree. */
export interface FileTreeNode {
  id: number;
  name: string;
  type: 'file' | 'folder';
  parentId: number | null;
  children?: FileTreeNode[];
  size?: number;
  url?: string;
  createdAt?: string;
}

// ── Map / Route Types ──────────────────────────────────────────────────

/** Map center coordinates. */
export interface MapCenter {
  lng: number;
  lat: number;
}

/** A POI marker on the map. */
export interface MapMarker {
  id: string;
  position: [number, number];
  title?: string;
  icon?: string;
}

/** A route segment. */
export interface RouteSegment {
  from: { name: string; lng: number; lat: number };
  to: { name: string; lng: number; lat: number };
  mode?: 'driving' | 'walking' | 'transit';
  distance?: number;
  duration?: number;
}

// ── Auth Types ─────────────────────────────────────────────────────────

/** Login request payload. */
export interface LoginRequest {
  username: string;
  password: string;
  captchaId?: string;
  captchaCode?: string;
}

/** Login response. */
export interface LoginResponse {
  code: number;
  message: string;
  data: {
    accessToken: string;
    refreshToken: string;
    user: UserInfo;
  };
}

/** Authenticated user info. */
export interface UserInfo {
  id: string;
  username: string;
  avatar?: string;
}
