<!-- ThinkCard — DeepSeek-style deep thinking / reasoning display -->
<template>
  <div class="think-card" :class="{ 'is-streaming': thinking, 'is-collapsed': !expanded }">
    <div class="think-header" @click="toggle">
      <div class="think-header-left">
        <template v-if="thinking">
          <!-- Thinking: brain icon pulsing -->
          <svg
            class="think-brain-icon pulse"
            viewBox="0 0 24 24"
            width="16"
            height="16"
            fill="none"
            stroke="currentColor"
            stroke-width="1.8"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <path d="M12 4a4 4 0 0 1 3.46 6 3.5 3.5 0 0 1 0 6 4 4 0 0 1-6.92 0 3.5 3.5 0 0 1 0-6A4 4 0 0 1 12 4z" />
            <path d="M9 12h.01" />
            <path d="M15 12h.01" />
            <path d="M10 16c.67.67 1.33 1 2 1s1.33-.33 2-1" />
          </svg>
          <span class="think-label">深度思考中</span>
          <span class="think-dots">
            <span class="dot" /><span class="dot" /><span class="dot" />
          </span>
        </template>
        <template v-else>
          <!-- Done: checkmark + duration -->
          <svg
            class="think-done-icon"
            viewBox="0 0 24 24"
            width="16"
            height="16"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <path d="M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20z" />
            <path d="M8 12l3 3 5-5" />
          </svg>
          <span class="think-label done">已深度思考</span>
          <template v-if="duration != null">
            <span class="think-meta">用时 {{ formatDuration(duration) }}</span>
          </template>
        </template>
      </div>
      <svg
        class="think-chevron"
        :class="{ rotated: expanded }"
        viewBox="0 0 24 24"
        width="14"
        height="14"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
      >
        <path d="M6 9l6 6 6-6" />
      </svg>
    </div>
    <div v-show="expanded" class="think-body-wrap">
      <div class="think-body">
        <div v-if="stepCount > 0" class="think-steps-badge">{{ stepCount }} 步推理</div>
        <div class="think-content">{{ content }}</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'

const props = defineProps<{
  content: string
  thinking?: boolean
  duration?: number
  startExpanded?: boolean
}>()

const expanded = ref(props.startExpanded ?? props.thinking ?? false)

function toggle() {
  expanded.value = !expanded.value
}

const stepCount = computed(() => {
  if (!props.content) return 0
  const lines = props.content.split('\n')
  let count = 0
  for (const line of lines) {
    const t = line.trim()
    if (/^(\d+[\.\)、]|第\d+步|步骤\d+|Step\s*\d+)/i.test(t)) count++
  }
  return count
})

function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms}ms`
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`
  const mins = Math.floor(ms / 60000)
  const secs = Math.round((ms % 60000) / 1000)
  return `${mins}m ${secs}s`
}
</script>

<style lang="scss" scoped>
.think-card {
  margin: 8px 0;
  border-radius: 10px;
  background: linear-gradient(135deg, #f5f3ff 0%, #f8f7ff 50%, #ede9fe 100%);
  border: 1px solid #e8e2f8;
  border-left: 3px solid #a78bfa;
  overflow: hidden;
  transition: border-color 0.3s, box-shadow 0.3s;

  &.is-streaming {
    border-left-color: #7c3aed;
    box-shadow: 0 0 0 1px rgba(124, 58, 237, 0.06);
    animation: think-glow 2s ease-in-out infinite;
  }

  &.is-collapsed {
    border-left-color: #d4c5f9;
  }
}

@keyframes think-glow {
  0%, 100% { box-shadow: 0 0 0 1px rgba(124, 58, 237, 0.03); }
  50%      { box-shadow: 0 0 0 2px rgba(124, 58, 237, 0.1); }
}

.think-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  cursor: pointer;
  user-select: none;
  transition: background 0.15s;

  &:hover {
    background: rgba(124, 58, 237, 0.04);
  }
}

.think-header-left {
  display: flex;
  align-items: center;
  gap: 7px;
  min-width: 0;
  flex: 1;
}

.think-brain-icon {
  color: #a78bfa;
  flex-shrink: 0;
  transition: color 0.3s, transform 0.3s;

  .is-streaming & { color: #7c3aed; }

  &.pulse {
    animation: brain-pulse 2s ease-in-out infinite;
  }
}

@keyframes brain-pulse {
  0%, 100% { transform: scale(1); opacity: 0.75; }
  50%      { transform: scale(1.06); opacity: 1; }
}

.think-done-icon {
  color: #8b5cf6;
  flex-shrink: 0;
}

.think-label {
  font-size: 13px;
  font-weight: 500;
  color: #6d5a9e;
  white-space: nowrap;

  .is-streaming & { color: #5b4a8a; }

  &.done { color: #7c6faa; }
}

.think-meta {
  font-size: 11px;
  color: #b4a5c8;
  white-space: nowrap;
  font-variant-numeric: tabular-nums;
  margin-left: 2px;
}

.think-dots {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  margin-left: 1px;

  .dot {
    width: 4px;
    height: 4px;
    border-radius: 50%;
    background: #a78bfa;
    animation: dot-wave 1.4s infinite both;

    &:nth-child(2) { animation-delay: 0.2s; }
    &:nth-child(3) { animation-delay: 0.4s; }
  }
}

@keyframes dot-wave {
  0%, 60%, 100% { opacity: 0.25; transform: translateY(0); }
  30%           { opacity: 1;    transform: translateY(-3px); }
}

.think-chevron {
  color: #c4b5d9;
  flex-shrink: 0;
  transition: transform 0.25s ease;
  margin-left: 8px;

  &.rotated { transform: rotate(180deg); }
}

.think-body-wrap {
  overflow: hidden;
}

.think-body {
  padding: 0 12px 10px;
  border-top: 1px solid #ece6f8;
  margin: 0 8px;
}

.think-steps-badge {
  display: inline-block;
  font-size: 10.5px;
  font-weight: 500;
  color: #8b7aa8;
  background: rgba(139, 122, 168, 0.08);
  border-radius: 5px;
  padding: 2px 8px;
  margin-bottom: 8px;
  margin-top: 8px;
}

.think-content {
  font-size: 12.5px;
  line-height: 1.65;
  color: #7a6e8c;
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 280px;
  overflow-y: auto;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'PingFang SC', 'Microsoft YaHei', sans-serif;

  &::-webkit-scrollbar { width: 4px; }
  &::-webkit-scrollbar-track { background: transparent; }
  &::-webkit-scrollbar-thumb { background: #d4c8e8; border-radius: 2px; }
}
</style>
