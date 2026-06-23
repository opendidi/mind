<template>
  <div class="agent-input" :class="{ focused }">
    <!-- Image preview strip -->
    <div v-if="images.length > 0" class="image-strip">
      <div v-for="(img, idx) in images" :key="idx" class="image-thumb">
        <img :src="img" alt="预览图片" />
        <button class="remove-btn" @click="removeImage(idx)" title="移除图片">
          <svg
            width="12"
            height="12"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="3"
            stroke-linecap="round"
          >
            <line x1="18" y1="6" x2="6" y2="18" />
            <line x1="6" y1="6" x2="18" y2="18" />
          </svg>
        </button>
      </div>
    </div>

    <div class="input-row">
      <textarea
        ref="textareaRef"
        v-model="inputText"
        :disabled="disabled"
        rows="1"
        placeholder="输入消息，Enter 发送，Shift+Enter 换行，Ctrl+V 粘贴图片..."
        @keydown="handleEnter"
        @focus="focused = true"
        @blur="focused = false"
        @paste="handlePaste"
      />

      <div class="btn-group">
        <button class="upload-btn" :disabled="disabled" @click="triggerUpload" title="上传图片">
          <svg
            width="18"
            height="18"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
            <circle cx="8.5" cy="8.5" r="1.5" />
            <polyline points="21 15 16 10 5 21" />
          </svg>
        </button>
        <input ref="fileInputRef" type="file" accept="image/*" hidden @change="handleFileChange" />

        <button class="send-btn" :disabled="disabled || (!inputText.trim() && images.length === 0)" @click="handleSend">
          <svg
            width="18"
            height="18"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <line x1="22" y1="2" x2="11" y2="13" />
            <polygon points="22 2 15 22 11 13 2 9 22 2" />
          </svg>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, nextTick } from 'vue'

const props = defineProps<{
  disabled: boolean
  initialValue?: string
}>()

const emit = defineEmits<{
  send: [text: string, images: string[]]
}>()

const inputText = ref('')
const images = ref<string[]>([])
const textareaRef = ref<HTMLTextAreaElement>()
const fileInputRef = ref<HTMLInputElement>()
const focused = ref(false)

// Apply preset context on mount
watch(
  () => props.initialValue,
  val => {
    if (val) {
      inputText.value = val
      nextTick(autoResize)
    }
  },
  { immediate: true },
)

// ── Image helpers ────────────────────────────────────────────────

function addImage(dataUrl: string) {
  images.value = [...images.value, dataUrl]
}

function removeImage(idx: number) {
  images.value = images.value.filter((_, i) => i !== idx)
}

function readFileAsDataURL(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(reader.result as string)
    reader.onerror = () => reject(reader.error)
    reader.readAsDataURL(file)
  })
}

async function handlePaste(e: ClipboardEvent) {
  const items = e.clipboardData?.items
  if (!items) return

  for (let i = 0; i < items.length; i++) {
    const item = items[i]
    if (item.type.startsWith('image/')) {
      e.preventDefault()
      const file = item.getAsFile()
      if (file) {
        try {
          const dataUrl = await readFileAsDataURL(file)
          addImage(dataUrl)
        } catch {
          // ignore failed reads
        }
      }
    }
  }
}

function triggerUpload() {
  fileInputRef.value?.click()
}

async function handleFileChange(e: Event) {
  const input = e.target as HTMLInputElement
  const files = input.files
  if (!files) return

  for (let i = 0; i < files.length; i++) {
    try {
      const dataUrl = await readFileAsDataURL(files[i])
      addImage(dataUrl)
    } catch {
      // ignore failed reads
    }
  }
  // Reset so the same file can be selected again
  input.value = ''
}

// ── Textarea auto-resize ─────────────────────────────────────────

const TEXTAREA_MAX_HEIGHT = 160

function autoResize() {
  const el = textareaRef.value
  if (!el) return
  // Reset to auto first so scrollHeight reflects the true content height
  el.style.height = 'auto'
  const h = Math.min(el.scrollHeight, TEXTAREA_MAX_HEIGHT)
  el.style.height = h + 'px'
  // Show native scrollbar only when content exceeds max height
  el.style.overflowY = el.scrollHeight > TEXTAREA_MAX_HEIGHT ? 'auto' : 'hidden'
}

// Also resize when images change (thumbnail strip affects available width → line wrap)
watch([inputText, images], () => nextTick(autoResize), { flush: 'post' })

// ── Send ─────────────────────────────────────────────────────────

function handleSend() {
  const text = inputText.value.trim()
  const hasText = !!text
  const hasImages = images.value.length > 0
  if ((!hasText && !hasImages) || props.disabled) return
  emit('send', text, [...images.value])
  inputText.value = ''
  images.value = []
  // Shrink textarea back to single-row after clearing
  nextTick(autoResize)
}

function handleEnter(e: KeyboardEvent) {
  if (e.key !== 'Enter') return
  if (e.shiftKey) return
  e.preventDefault()
  handleSend()
}
</script>

<style scoped lang="less">
.agent-input {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 6px 6px 6px 14px;
  border: 1px solid #e0e0e0;
  border-radius: 12px;
  background: #fff;
  transition:
    border-color 0.2s,
    box-shadow 0.2s;

  &.focused {
    border-color: #1677ff;
    box-shadow: 0 0 0 2px rgba(22, 119, 255, 0.12);
  }

  .image-strip {
    display: flex;
    gap: 6px;
    padding: 4px 0 2px;
    overflow-x: auto;

    .image-thumb {
      position: relative;
      flex-shrink: 0;
      width: 56px;
      height: 56px;
      border-radius: 6px;
      overflow: hidden;
      border: 1px solid #eee;
      background: #f5f5f5;

      img {
        width: 100%;
        height: 100%;
        object-fit: cover;
      }

      .remove-btn {
        position: absolute;
        top: 1px;
        right: 1px;
        width: 18px;
        height: 18px;
        border: none;
        border-radius: 50%;
        background: rgba(0, 0, 0, 0.55);
        color: #fff;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 0;
        opacity: 0;
        transition: opacity 0.15s;
      }

      &:hover .remove-btn {
        opacity: 1;
      }
    }
  }

  .input-row {
    display: flex;
    align-items: flex-end;
    gap: 6px;
  }

  textarea {
    flex: 1;
    min-width: 0;
    border: none;
    outline: none;
    resize: none;
    font-size: 14px;
    line-height: 1.5;
    font-family: inherit;
    padding: 4px 0;
    background: transparent;
    color: #333;
    overflow-y: hidden;
    transition: height 0.12s ease-out;

    &::placeholder {
      color: #bfbfbf;
    }

    &:disabled {
      color: #999;
    }
  }

  .btn-group {
    display: flex;
    align-items: center;
    gap: 4px;
    flex-shrink: 0;
  }

  .upload-btn {
    flex-shrink: 0;
    width: 32px;
    height: 32px;
    border: none;
    border-radius: 8px;
    background: transparent;
    color: #888;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    transition:
      color 0.2s,
      background 0.2s;

    &:hover:not(:disabled) {
      color: #1677ff;
      background: rgba(22, 119, 255, 0.08);
    }

    &:disabled {
      color: #d9d9d9;
      cursor: not-allowed;
    }
  }

  .send-btn {
    flex-shrink: 0;
    width: 32px;
    height: 32px;
    border: none;
    border-radius: 8px;
    background: #1677ff;
    color: #fff;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    transition:
      background 0.2s,
      opacity 0.2s;

    &:hover:not(:disabled) {
      background: #4096ff;
    }

    &:disabled {
      background: #d9d9d9;
      cursor: not-allowed;
      opacity: 0.6;
    }
  }
}
</style>
