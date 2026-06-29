<!-- Translate popover — shows translation result -->
<template>
  <teleport to="body">
    <div class="translate-overlay" @click.self="$emit('close')">
      <div class="translate-popover" :style="popoverStyle">
        <div class="tp-header">
          <span class="tp-langs flex">
            <span class="tp-lang-tag">{{ sourceLabel }}</span>
            <span class="tp-swap" title="交换语言" @click="onSwap">⇄</span>
            <a-dropdown :trigger="['click']" placement="bottom" :getPopupContainer="(t: any) => t.parentNode">
              <span class="tp-lang-tag tp-lang-target flex items-center">
                <span class="mr-1">{{ targetLabel }}</span>
                <CaretDownFilled style="font-size: 12px" />
              </span>
              <template #overlay>
                <a-menu @click="onSelectTarget">
                  <template v-for="l in quickLangs" :key="l.code">
                    <a-menu-item :disabled="l.code === sourceLang">
                      {{ l.label }}
                    </a-menu-item>
                  </template>
                </a-menu>
              </template>
            </a-dropdown>
          </span>
          <span class="tp-style-btns">
            <template v-for="s in styleOptions" :key="s.key">
              <button class="tp-style-btn" :class="{ active: (props.style || 'general') === s.key }" @click="emit('changeStyle', s.key)">{{ s.label }}</button>
            </template>
          </span>
          <span class="tp-engine" :class="engine">{{ engine }}</span>
          <span class="tp-close" @click="$emit('close')">✕</span>
        </div>
        <div class="tp-body">
          <template v-if="loading">
            <div class="tp-loading">
              <span class="tp-spinner"></span>
              <span>翻译中...</span>
            </div>
          </template>
          <template v-else-if="error">
            <div class="tp-error">{{ error }}</div>
          </template>
          <template v-else>
            <div class="tp-text">{{ translated }}</div>
          </template>
        </div>
        <div class="tp-footer flex justify-end items-center">
          <a-button @click="copyResult">
            <CopyOutlined />
            <span>复制</span>
          </a-button>
          <a-divider type="vertical" />
          <a-button v-if="ttsSupported" @click="speakResult">
            <template v-if="ttsSpeaking">
              <PauseCircleFilled />
            </template>
            <template v-else>
              <SoundOutlined />
            </template>
            <span>朗读</span>
          </a-button>
        </div>
      </div>
    </div>
  </teleport>
</template>

<script setup lang="ts">
import { computed, onMounted, onBeforeUnmount } from 'vue'
import { CopyOutlined, CaretDownFilled, SoundOutlined, PauseCircleFilled } from '@ant-design/icons-vue'
import { message } from 'ant-design-vue'
import { useSpeech } from '@/composables/useSpeech'

const props = defineProps<{
  x: number
  y: number
  loading: boolean
  error: string
  translated: string
  engine: string
  sourceLang: string
  targetLang: string
  style?: string
}>()

const emit = defineEmits<{
  close: []
  changeTarget: [lang: string]
  changeStyle: [style: string]
}>()

const styleOptions = [
  { key: 'general', label: '通用' },
  { key: 'formal', label: '正式' },
  { key: 'technical', label: '技术' },
]

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Escape') emit('close')
}

onMounted(() => document.addEventListener('keydown', onKeydown))
onBeforeUnmount(() => document.removeEventListener('keydown', onKeydown))

const langLabels: Record<string, string> = {
  zh: '中文',
  en: '英语',
  ja: '日语',
  ko: '韩语',
  fr: '法语',
  de: '德语',
  es: '西班牙语',
  pt: '葡萄牙语',
  it: '意大利语',
  ru: '俄语',
  ar: '阿拉伯语',
}

const quickLangs = [
  { code: 'zh', label: '中文' },
  { code: 'en', label: 'English' },
  { code: 'ja', label: '日本語' },
  { code: 'ko', label: '한국어' },
  { code: 'fr', label: 'Français' },
  { code: 'de', label: 'Deutsch' },
  { code: 'es', label: 'Español' },
]

const { speaking: ttsSpeaking, supported: ttsSupported, speak } = useSpeech()

const sourceLabel = computed(() => langLabels[props.sourceLang] || props.sourceLang || '自动检测')
const targetLabel = computed(() => langLabels[props.targetLang] || props.targetLang)

function onSelectTarget({ key }: { key: string }) {
  emit('changeTarget', key)
}

function onSwap() {
  emit('changeTarget', props.sourceLang)
}

const popoverStyle = computed(() => {
  const w = Math.min(380, window.innerWidth - 32)
  let left = props.x
  if (left + w > window.innerWidth - 16) left = window.innerWidth - w - 16
  if (left < 16) left = 16
  return {
    left: `${left}px`,
    top: `${Math.min(props.y + 8, window.innerHeight - 260)}px`,
  }
})

function copyResult() {
  navigator.clipboard.writeText(props.translated).then(() => {
    message.success('已复制')
  })
}

function speakResult() {
  if (props.translated) speak(props.translated)
}
</script>

<style lang="scss" scoped>
.translate-overlay {
  position: fixed;
  inset: 0;
  z-index: 9999;
}

.translate-popover {
  position: fixed;
  width: 100%;
  max-width: 380px;
  background: #fff;
  border-radius: 10px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.18);
  border: 1px solid #e5e7eb;
  z-index: 10000;
  font-size: 14px;
}

.tp-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  border-bottom: 1px solid #f1f5f9;
  .tp-langs {
    .tp-lang-tag {
      font-size: 12px;
      color: #64748b;
      background: #f1f5f9;
      padding: 2px 8px;
      border-radius: 4px;
    }
  }
}

.tp-swap {
  cursor: pointer;
  color: #94a3b8;
  font-size: 14px;
  padding: 0 2px;
  &:hover {
    color: #6366f1;
  }
}

.tp-lang-target {
  cursor: pointer;
  &:hover {
    background: #e2e8f0;
  }
}

.tp-engine {
  font-size: 11px;
  color: #fff;
  background: #22d3ee;
  padding: 1px 6px;
  border-radius: 3px;
  margin-left: auto;

  &.argos {
    background: #10b981;
  }
  &.llm {
    background: #6366f1;
  }
}

.tp-style-btns {
  display: flex;
  gap: 2px;
  margin-left: auto;
  margin-right: 4px;
}

.tp-style-btn {
  border: none;
  background: transparent;
  font-size: 11px;
  color: #94a3b8;
  padding: 2px 6px;
  border-radius: 3px;
  cursor: pointer;
  transition: all 0.12s;
  font-family: inherit;

  &:hover {
    background: #f1f5f9;
    color: #64748b;
  }
  &.active {
    background: #eef2ff;
    color: #6366f1;
    font-weight: 500;
  }
}

.tp-close {
  cursor: pointer;
  color: #94a3b8;
  font-size: 14px;
  padding: 2px;
  line-height: 1;

  &:hover {
    color: #475569;
  }
}

.tp-body {
  padding: 12px 14px;
  min-height: 60px;
  max-height: 200px;
  overflow-y: auto;
}

.tp-loading {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #94a3b8;
  font-size: 13px;
}

.tp-spinner {
  width: 16px;
  height: 16px;
  border: 2px solid #e2e8f0;
  border-top-color: #6366f1;
  border-radius: 50%;
  animation: tp-spin 0.6s linear infinite;
}

@keyframes tp-spin {
  to {
    transform: rotate(360deg);
  }
}

.tp-error {
  color: #ef4444;
  font-size: 13px;
}

.tp-text {
  color: #1e293b;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
}

.tp-footer {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 4px;
  padding: 8px 14px;
  border-top: 1px solid #f1f5f9;

  :deep(.ant-btn) {
    display: inline-flex;
    align-items: center;
    gap: 4px;
  }
}
</style>