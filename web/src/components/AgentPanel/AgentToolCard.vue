<template>
  <div class="tool-card mb-1" :class="`tool-${toolCall.status}`">
    <div class="tool-header">
      <span class="tool-status-icon">
        <span v-if="toolCall.status === 'running'">⏳</span>
        <span v-else-if="toolCall.status === 'success'">✅</span>
        <span v-else-if="toolCall.status === 'error'">❌</span>
        <span v-else>🔧</span>
      </span>
      <span class="tool-name">{{ displayName }}</span>
    </div>
    <div class="tool-body">
      <div class="tool-args">{{ summary }}</div>
      <template v-if="toolCall.status === 'success' && mutationSummary">
        <div class="tool-mutation">{{ mutationSummary }}</div>
      </template>
      <template v-if="toolCall.status === 'error' && toolCall.result">
        <div class="tool-error">
          {{ resultAny?.error || resultAny?.message || '执行失败' }}
        </div>
      </template>
    </div>
    <template v-if="showLocate">
      <div class="tool-footer">
        <a-button size="small" type="link" @click="onLocateClick">📍 定位</a-button>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { getCanvasMutationSummary } from '@/utils/canvasBridge'
import type { ToolCallRecord } from './AgentStreamHandler'

const props = defineProps<{
  toolCall: ToolCallRecord
}>()

const emit = defineEmits<{
  locatePens: [ids: string[]]
}>()

const isCanvasTool = computed(() => {
  const t = props.toolCall.tool
  return t === 'canvas' || t.startsWith('canvas_')
})

const displayName = computed(() => {
  const { tool, args } = props.toolCall
  if (isCanvasTool.value && args?.action) {
    const labels: Record<string, string> = {
      add_pen: '创建图形',
      add_line: '创建连线',
      add_diagram: '创建图表',
      update_pen: '修改图形',
      delete_pen: '删除图形',
      get_state: '查询状态',
      clear: '清空画布',
      undo: '撤销',
      redo: '重做',
      layout_auto_arrange: '自动排列',
      layout_align: '对齐',
    }
    return `画布 / ${labels[args.action as string] || args.action}`
  }
  return tool
})

const mutationSummary = computed(() => {
  const { tool, args, success, result } = props.toolCall
  if (!isCanvasTool.value) return null
  return getCanvasMutationSummary(tool, args, success ?? false, result)
})

/** Whether to show a "locate" button for this tool result */
const showLocate = computed(() => {
  if (props.toolCall.status !== 'success') return false
  if (!isCanvasTool.value) return false
  const action = props.toolCall.args?.action as string
  // Only for tools that create or modify visible elements
  return ['add_pen', 'canvas_add_pen', 'add_diagram', 'canvas_add_diagram', 'update_pen', 'canvas_update_pen'].includes(
    action || props.toolCall.tool,
  )
})

function onLocateClick() {
  const args = props.toolCall.args
  const result = props.toolCall.result as Record<string, unknown> | undefined
  const action = (args?.action as string) || props.toolCall.tool
  const ids: string[] = []

  switch (action) {
    case 'add_pen':
    case 'canvas_add_pen': {
      const penId = (result?.pen_id || result?.penId) as string
      if (penId) ids.push(penId)
      break
    }
    case 'update_pen':
    case 'canvas_update_pen': {
      const pid = (args?.pen_id as string) || ''
      if (pid) ids.push(pid)
      break
    }
    case 'add_diagram':
    case 'canvas_add_diagram': {
      const diag = (result?.data as Record<string, unknown>)?.diagram as Record<string, unknown> | undefined
      const nodes = (diag?.nodes || []) as Record<string, unknown>[]
      for (const n of nodes) {
        const id = (n.pen_id || n.id) as string
        if (id) ids.push(id)
      }
      break
    }
  }

  if (ids.length) emit('locatePens', ids)
}

const resultAny = computed(() => props.toolCall.result as any)

const summary = computed(() => {
  const { args } = props.toolCall
  if (!args || Object.keys(args).length === 0) return '无参数'

  if (isCanvasTool.value) {
    return formatCanvas(args, props.toolCall.result)
  }
  return formatGeneric(args)
})

function formatCanvas(args: Record<string, unknown>, result: unknown): string {
  const action = args.action as string
  switch (action) {
    case 'add_pen': {
      const type = args.type || 'rectangle'
      const text = args.text ? `"${args.text}"` : ''
      const x = args.x ?? 0
      const y = args.y ?? 0
      const w = args.width ?? 120
      const h = args.height ?? 60
      return `${type} ${text} (${x}, ${y}) ${w}x${h}`
    }
    case 'add_line': {
      const from = args.from_pen || '?'
      const to = args.to_pen || '?'
      const text = args.text ? ` "${args.text}"` : ''
      return `${from} → ${to}${text}`
    }
    case 'update_pen': {
      const pid = args.pen_id || '?'
      const props = args.props as Record<string, unknown> | undefined
      const keys = props ? Object.keys(props).join(', ') : ''
      return `${pid}: ${keys}`
    }
    case 'delete_pen': {
      const ids = (args.pen_ids as string[]) || (args.pen_id ? [args.pen_id as string] : [])
      return `删除 ${ids.length} 个图形`
    }
    case 'add_diagram': {
      const r = result as Record<string, unknown> | undefined
      const diag = (r?.data as Record<string, unknown>)?.diagram as Record<string, unknown> | undefined
      const nCount = ((diag?.nodes as any[]) || []).length
      const eCount = ((diag?.edges as any[]) || []).length
      return `${nCount} 节点, ${eCount} 连线`
    }
    case 'clear':
      return args.confirm ? '已确认清空' : '未确认'
    case 'undo':
    case 'redo':
    case 'get_state':
      return action === 'get_state' ? '查看画布状态' : action === 'undo' ? '撤销' : '重做'
    default:
      return formatGeneric(args)
  }
}

function formatGeneric(args: Record<string, unknown>): string {
  const parts: string[] = []
  for (const [k, v] of Object.entries(args)) {
    const val = typeof v === 'string' ? (v.length > 40 ? v.slice(0, 40) + '...' : v) : String(v)
    parts.push(`${k}=${val}`)
  }
  return parts.join(', ')
}
</script>

<style scoped lang="less">
.tool-card {
  border-radius: 6px;
  border-left: 3px solid #d9d9d9;
  background: #fafafa;
  padding: 6px 10px;
  font-size: 13px;

  &.tool-success {
    border-color: #52c41a;
    background: #f6ffed;
  }

  &.tool-error {
    border-color: #ff4d4f;
    background: #fff2f0;
  }

  &.tool-running {
    border-color: #1677ff;
    background: #f0f5ff;
  }
}

.tool-header {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 4px;
}

.tool-status-icon {
  font-size: 14px;
}

.tool-name {
  font-weight: 500;
  color: #333;
}

.tool-args {
  font-size: 12px;
  color: #888;
  word-break: break-all;
  overflow-wrap: break-word;
}

.tool-mutation {
  margin-top: 4px;
  font-size: 12px;
  color: #389e0d;
  font-weight: 500;
}

.tool-error {
  margin-top: 4px;
  font-size: 12px;
  color: #ff4d4f;
}

.tool-footer {
  margin-top: 6px;
  border-top: 1px solid #e8e8e8;
  padding-top: 4px;
}
</style>
