<template>
  <div class="tool-card" :class="`tool-${toolCall.status}`">
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
      <div v-if="toolCall.status === 'error' && toolCall.result" class="tool-error">
        {{ toolCall.result?.error || toolCall.result?.message || '执行失败' }}
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { ToolCallRecord } from './AgentStreamHandler'

const props = defineProps<{
  toolCall: ToolCallRecord
}>()

const displayName = computed(() => {
  const { tool, args } = props.toolCall
  if ((tool === 'canvas' || tool.startsWith('canvas_')) && args?.action) {
    const labels: Record<string, string> = {
      add_pen: '创建图形',
      add_line: '创建连线',
      update_pen: '修改图形',
      delete_pen: '删除图形',
      get_state: '查询状态',
      clear: '清空画布',
      undo: '撤销',
      redo: '重做',
    }
    return `画布 / ${labels[args.action as string] || args.action}`
  }
  return tool
})

const summary = computed(() => {
  const { tool, args } = props.toolCall
  if (!args || Object.keys(args).length === 0) return '无参数'

  if (tool === 'canvas' || tool.startsWith('canvas_')) {
    return formatCanvas(args)
  }
  return formatGeneric(args)
})

function formatCanvas(args: Record<string, unknown>): string {
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

.tool-error {
  margin-top: 4px;
  font-size: 12px;
  color: #ff4d4f;
}
</style>
