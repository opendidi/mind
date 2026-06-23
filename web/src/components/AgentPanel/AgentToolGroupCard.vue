<template>
  <div class="tool-group-card">
    <div class="group-header" @click="expanded = !expanded">
      <span class="group-icon">🔧</span>
      <span class="group-label">画布操作 ({{ toolCalls.length }})</span>
      <span class="group-toggle">{{ expanded ? '▾' : '▸' }}</span>
    </div>
    <div v-if="expanded" class="group-body">
      <AgentToolCard v-for="tc in toolCalls" :key="tc.id" :tool-call="tc" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import type { ToolCallRecord } from './AgentStreamHandler'
import AgentToolCard from './AgentToolCard.vue'

defineProps<{
  toolCalls: ToolCallRecord[]
}>()

const expanded = ref(false)
</script>

<style scoped lang="less">
.tool-group-card {
  border: 1px solid #d9d9d9;
  border-radius: 6px;
  background: #fafafa;
  font-size: 13px;
}

.group-header {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 10px;
  cursor: pointer;
  color: #666;
  user-select: none;

  &:hover {
    color: #333;
    background: #f0f0f0;
    border-radius: 6px 6px 0 0;
  }
}

.group-icon {
  font-size: 14px;
}

.group-label {
  font-weight: 500;
}

.group-toggle {
  margin-left: auto;
  font-size: 12px;
}

.group-body {
  padding: 6px 8px 8px;
  border-top: 1px solid #eee;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
</style>
