<template>
  <div class="msg-actions">
    <span class="msg-copy" title="复制" @click="$emit('copy')"><CopyOutlined /></span>
    <span
      class="msg-quote-btn"
      title="引用"
      :style="flipQuote ? 'transform: scaleX(-1)' : ''"
      @click="$emit('quote')"
    >
      <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M9 17L4 12l5-5" />
        <path d="M4 12h10a6 6 0 010 12" />
      </svg>
    </span>
    <template v-if="showFeedback">
      <span class="msg-feedback" :class="feedbackClass">
        <span class="fb-btn" title="有帮助" @click="$emit('feedback', 'liked')"><LikeOutlined /></span>
        <span class="fb-btn" title="无帮助" @click="$emit('feedback', 'disliked')"><DislikeOutlined /></span>
      </span>
    </template>
    <template v-if="showTts">
      <span
        class="msg-speak"
        :class="{ active: ttsSpeaking }"
        :title="ttsSpeaking ? '停止朗读' : '朗读'"
        @click="$emit('toggleSpeak')"
      >
        <template v-if="!ttsSpeaking">
          <SoundOutlined />
        </template>
        <template v-else>
          <PauseCircleFilled />
        </template>
      </span>
    </template>
    <template v-if="!selectable">
      <span class="msg-select-trigger" title="选择" @click="$emit('startSelect')">
        <CheckSquareOutlined />
      </span>
    </template>
  </div>
</template>

<script setup lang="ts">
import { CopyOutlined, CheckSquareOutlined, LikeOutlined, DislikeOutlined, SoundOutlined, PauseCircleFilled } from '@ant-design/icons-vue'

defineProps<{
  flipQuote?: boolean
  showFeedback?: boolean
  feedbackClass?: Record<string, boolean>
  showTts?: boolean
  ttsSpeaking?: boolean
  selectable?: boolean
}>()

defineEmits<{
  copy: []
  quote: []
  feedback: [type: string]
  toggleSpeak: []
  startSelect: []
}>()
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;

.msg-actions {
  display: flex;
  align-items: center;
  gap: 2px;
  margin-top: 4px;
}

.msg-copy,
.msg-quote-btn,
.msg-select-trigger {
  display: inline-flex;
  align-items: center;
  padding: 3px 6px;
  font-size: 12px;
  color: $text-muted;
  cursor: pointer;
  border-radius: 4px;
  transition: all 0.15s;
  opacity: 0;
  &:hover {
    color: $primary;
    background: #f1f5f9;
  }
}

.msg-speak {
  display: inline-flex;
  align-items: center;
  padding: 3px 6px;
  font-size: 12px;
  color: $text-muted;
  cursor: pointer;
  border-radius: 4px;
  transition: all 0.15s;
  opacity: 0;
  &:hover {
    color: $primary;
    background: #f1f5f9;
  }
  &.active {
    opacity: 1;
    color: $primary;
    background: #eef2ff;
  }
}

.msg-feedback {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  opacity: 0;
  .fb-btn {
    display: inline-flex;
    align-items: center;
    padding: 3px 5px;
    font-size: 12px;
    color: $text-muted;
    cursor: pointer;
    border-radius: 4px;
    transition: all 0.15s;
    &:hover {
      color: $primary;
      background: #f1f5f9;
    }
  }
  &.liked,
  &.disliked {
    opacity: 1;
  }
  &.liked .fb-btn:first-child {
    color: $primary;
  }
  &.disliked .fb-btn:last-child {
    color: #dc2626;
  }
}
</style>
