<template>
  <Teleport to="body">
    <transition name="quote-fade">
      <template v-if="visible">
        <div class="selection-toolbar" :style="{ left: `${x}px`, top: `${y}px` }">
          <span class="toolbar-btn" @click.stop="$emit('quote')">
            <svg
              viewBox="0 0 24 24"
              width="14"
              height="14"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              style="transform: scale(-1, -1)"
            >
              <path d="M9 17L4 12l5-5" />
              <path d="M4 12h10a6 6 0 010 12" />
            </svg>
            <span>引用</span>
          </span>
          <span class="toolbar-divider"></span>
          <span class="toolbar-btn" @click.stop="$emit('copy')">
            <CopyOutlined />
            <span>复制</span>
          </span>
          <span class="toolbar-divider"></span>
          <span class="toolbar-btn" @click.stop="$emit('translate')">
            <TranslationOutlined />
            <span>翻译</span>
          </span>
          <template v-if="ttsSupported">
            <span class="toolbar-divider"></span>
            <span class="toolbar-btn" @click.stop="$emit('speak')">
              <SoundOutlined />
              <span>朗读</span>
            </span>
          </template>
        </div>
      </template>
    </transition>
  </Teleport>
</template>

<script setup lang="ts">
import { CopyOutlined, SoundOutlined, TranslationOutlined } from '@ant-design/icons-vue'

defineProps<{
  x: number
  y: number
  visible: boolean
  ttsSupported: boolean
}>()

defineEmits<{
  copy: []
  quote: []
  translate: []
  speak: []
}>()
</script>

<style lang="scss" scoped>
.selection-toolbar {
  position: fixed;
  z-index: 999;
  display: flex;
  align-items: center;
  padding: 4px 6px;
  background: #fff;
  border-radius: 10px;
  box-shadow: 0 4px 20px rgba(79, 70, 229, 0.12), 0 2px 8px rgba(0, 0, 0, 0.06), 0 0 0 0.5px rgba(0, 0, 0, 0.06);
  transform: none;
  transition: box-shadow 0.2s, transform 0.15s;
  user-select: none;

  .toolbar-btn {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 4px 10px;
    font-size: 13px;
    font-weight: 500;
    color: #333;
    cursor: pointer;
    border-radius: 6px;
    transition: background 0.12s;
    &:hover {
      background: rgba(79, 70, 229, 0.06);
    }
    &:active {
      transform: scale(0.96);
    }
  }
  .toolbar-divider {
    width: 1px;
    height: 18px;
    background: #e2e8f0;
    margin: 0 2px;
  }
}

.quote-fade-enter-active,
.quote-fade-leave-active {
  transition: opacity 0.12s ease;
}
.quote-fade-enter-from,
.quote-fade-leave-to {
  opacity: 0;
}
</style>
