<template>
  <div class="think-card">
    <div class="think-header" @click="expanded = !expanded">
      <span class="think-icon">💭</span>
      <span>思考过程</span>
      <span class="think-toggle">{{ expanded ? '▾' : '▸' }}</span>
    </div>
    <div v-if="expanded" class="think-body">
      {{ content }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

defineProps<{
  content: string
}>()

const expanded = ref(false)
</script>

<style scoped lang="less">
.think-card {
  border: 1px solid #e8e8e8;
  border-radius: 6px;
  background: #fafafa;
  font-size: 13px;
}

.think-header {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 10px;
  cursor: pointer;
  color: #888;
  user-select: none;

  &:hover {
    color: #555;
  }
}

.think-icon {
  font-size: 14px;
}

.think-toggle {
  margin-left: auto;
  font-size: 12px;
}

.think-body {
  padding: 8px 12px 12px;
  border-top: 1px solid #f0f0f0;
  color: #666;
  line-height: 1.5;
  white-space: pre-wrap;
}
</style>
