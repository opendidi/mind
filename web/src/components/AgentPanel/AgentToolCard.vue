<template>
  <div class="tool-card" :class="`tool-${toolCall.status}`">
    <div class="tool-header">
      <span class="tool-status-icon">
        <span v-if="toolCall.status === 'running'">⏳</span>
        <span v-else-if="toolCall.status === 'success'">✅</span>
        <span v-else-if="toolCall.status === 'error'">❌</span>
        <span v-else>🔧</span>
      </span>
      <span class="tool-name">{{ toolCall.tool }}</span>
    </div>
    <div class="tool-body">
      <div class="tool-args">
        <code>{{ formatArgs(toolCall.args) }}</code>
      </div>
      <div v-if="toolCall.status === 'error' && toolCall.result" class="tool-error">
        {{ toolCall.result?.error || toolCall.result?.message || '执行失败' }}
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { ToolCallRecord } from './AgentStreamHandler';

defineProps<{
  toolCall: ToolCallRecord;
}>();

function formatArgs(args: any): string {
  if (!args || Object.keys(args).length === 0) return '{}';
  const simplified: Record<string, any> = {};
  for (const [k, v] of Object.entries(args)) {
    if (typeof v === 'string' && v.length > 80) {
      simplified[k] = v.slice(0, 80) + '...';
    } else {
      simplified[k] = v;
    }
  }
  return JSON.stringify(simplified, null, 0).replace(/[{}"]/g, '').replace(/,/g, ', ');
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
  font-family: monospace;
}

.tool-args {
  code {
    font-size: 12px;
    color: #888;
    word-break: break-all;
  }
}

.tool-error {
  margin-top: 4px;
  font-size: 12px;
  color: #ff4d4f;
}
</style>
