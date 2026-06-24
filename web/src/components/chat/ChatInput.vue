<!-- Chat input area -- text input + send/abort + file uploads -->
<template>
  <div class="input-area">
    <!-- Quote preview -->
    <div v-if="quotedText" class="quote-bar">
      <span class="quote-label">
        {{ quotedText.role === 'user' ? '你' : 'AI' }}
      </span>
      <span class="quote-preview">{{ quotedText.text }}</span>
      <a-button type="text" size="small" class="quote-close" @click="$emit('removeQuote')">
        <CloseOutlined />
      </a-button>
    </div>

    <!-- Image attachment previews -->
    <div v-if="attachments.length > 0" class="attach-preview-row">
      <div
        v-for="(att, idx) in attachments"
        :key="'img-' + idx"
        class="attach-thumb"
        :class="{ uploading: att.uploading, failed: att.failed }"
      >
        <img v-if="!att.failed" :src="att.preview" :alt="att.name" />
        <span v-else class="attach-fail-icon">!</span>
        <span v-if="att.uploading" class="attach-spin" />
        <span class="attach-remove" @click="onRemoveAttachment(idx)">&times;</span>
      </div>
    </div>

    <!-- Document attachment previews -->
    <div v-if="docAttachments.length > 0" class="attach-preview-row">
      <div
        v-for="(doc, idx) in docAttachments"
        :key="'doc-' + idx"
        class="doc-attach"
        :class="{ uploading: doc.uploading, failed: doc.failed }"
      >
        <FileTextOutlined class="doc-icon" />
        <span class="doc-name">{{ doc.name }}</span>
        <span v-if="doc.uploading" class="attach-spin" />
        <span v-else-if="!doc.failed" class="doc-ok">&#10003;</span>
        <span class="attach-remove" @click="onRemoveDoc(idx)">&times;</span>
      </div>
    </div>

    <!-- Model selection -->
    <div v-if="modelList.length > 0" class="model-row">
      <template v-for="(item, idx) in modelList" :key="item.id">
        <span class="model-chip" :class="{ active: modelIdx === idx }" @click="$emit('update:modelIdx', idx)">
          {{ item.id }}
        </span>
      </template>
    </div>

    <!-- Hidden file inputs -->
    <input ref="imgInputRef" type="file" accept="image/*" multiple hidden @change="onFileChange" />
    <input ref="docInputRef" type="file" accept=".docx,.xlsx,.xls,.txt,.json" hidden @change="onDocFileChange" />

    <!-- Input box -->
    <div class="input-inner">
      <textarea
        ref="textareaRef"
        v-model="inputText"
        rows="1"
        @input="onTextareaInput"
        placeholder="输入你的问题，Enter 发送，Shift+Enter 换行"
        :disabled="loading"
        @keydown="onKeydown"
      />
      <div class="input-actions">
        <!-- Image upload button -->
        <a-tooltip title="上传图片">
          <a-button type="text" class="tool-btn" :disabled="loading" @click="imgInputRef?.click()">
            <PaperClipOutlined />
          </a-button>
        </a-tooltip>
        <!-- Document upload button -->
        <a-tooltip title="上传文档 (.docx/.xlsx/.txt/.json)">
          <a-button type="text" class="tool-btn" :disabled="loading" @click="docInputRef?.click()">
            <FileTextOutlined />
          </a-button>
        </a-tooltip>
        <template v-if="loading">
          <a-button type="primary" danger @click="$emit('abort')" class="abort-btn" title="停止生成">
            <CloseOutlined />
          </a-button>
        </template>
        <template v-else>
          <a-button type="primary" :disabled="!canSend" @click="onSend" class="send-btn">
            <SendOutlined />
          </a-button>
        </template>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, nextTick } from 'vue'
import { CloseOutlined, SendOutlined, PaperClipOutlined, FileTextOutlined, SmileOutlined } from '@ant-design/icons-vue'
import { message } from 'ant-design-vue'
import data from '@emoji-mart/data'
import Picker from 'emoji-mart-vue-fast'
import type { QuoteInfo, ChatFile } from '@/composables/useAgentChat'
import { useAttachments } from '@/composables/useAttachments'
import { apiChatUploadFile } from '@/api/chat'

const props = defineProps<{
  loading: boolean
  modelList?: { id: string }[]
  modelIdx?: number
  quotedText?: QuoteInfo | null
}>()

const emit = defineEmits<{
  'update:modelIdx': [idx: number]
  send: [text: string, imageUrls: string[], docMarkers: string[], docFiles: ChatFile[], quotedText?: QuoteInfo]
  abort: []
  removeQuote: []
}>()

const inputText = ref('')
const textareaRef = ref<HTMLTextAreaElement | null>(null)
const imgInputRef = ref<HTMLInputElement | null>(null)
const docInputRef = ref<HTMLInputElement | null>(null)

// Image attachments via composable
const { attachments, onFileChange, onRemoveAttachment, cleanup } = useAttachments()

// Document attachments
interface DocAttach {
  name: string
  objectName: string
  url: string
  uploading: boolean
  failed: boolean
}
const docAttachments = ref<DocAttach[]>([])

// Emoji picker
const showEmoji = ref(false)

async function onDocFileChange(e: Event) {
  const input = e.target as HTMLInputElement
  const files = input.files
  if (!files || files.length === 0) return

  for (let i = 0; i < files.length; i++) {
    const file = files[i]
    const item: DocAttach = {
      name: file.name,
      objectName: '',
      url: '',
      uploading: true,
      failed: false,
    }
    docAttachments.value.push(item)
    const idx = docAttachments.value.length - 1

    try {
      const res = await apiChatUploadFile(file)
      docAttachments.value[idx].objectName = res.object_name
      docAttachments.value[idx].url = res.url
      docAttachments.value[idx].uploading = false
    } catch (err: unknown) {
      docAttachments.value[idx].failed = true
      docAttachments.value[idx].uploading = false
      if (err?.message && !err?.response) {
        message.error(err.message)
      }
    }
  }

  input.value = ''
}

function onRemoveDoc(idx: number) {
  docAttachments.value.splice(idx, 1)
}

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) {
    e.preventDefault()
    onSend()
  }
}

function onTextareaInput() {
  const el = textareaRef.value
  if (!el) return
  el.style.height = 'auto'
  el.style.height = Math.min(el.scrollHeight, 160) + 'px'
}

function onEmojiSelect(emoji: { native: string }) {
  const el = textareaRef.value
  if (!el) return
  const start = el.selectionStart
  const end = el.selectionEnd
  const before = inputText.value.slice(0, start)
  const after = inputText.value.slice(end)
  inputText.value = before + emoji.native + after
  showEmoji.value = false
  nextTick(() => {
    el.focus()
    const pos = start + emoji.native.length
    el.selectionStart = pos
    el.selectionEnd = pos
  })
}

const hasReadyImages = computed(() => attachments.value.some(a => !a.uploading && !a.failed && a.url))
const hasReadyDocs = computed(() => docAttachments.value.some(d => !d.uploading && !d.failed && d.objectName))
const hasUploading = computed(
  () => attachments.value.some(a => a.uploading) || docAttachments.value.some(d => d.uploading),
)
const canSend = computed(
  () =>
    (inputText.value.trim().length > 0 || hasReadyImages.value || hasReadyDocs.value || !!props.quotedText) &&
    !hasUploading.value,
)

function onSend() {
  const text = inputText.value.trim()
  const hasQuote = !!props.quotedText
  if (!canSend.value || props.loading) return

  inputText.value = ''
  if (textareaRef.value) textareaRef.value.style.height = ''

  const imageUrls = attachments.value.filter(a => !a.failed && a.url).map(a => a.url)

  const readyDocs = docAttachments.value.filter(d => !d.failed && d.objectName)

  const docMarkers = readyDocs.map(d => `[上传文件: ${d.objectName} (${d.name})]`)

  const docFiles = readyDocs.map(d => ({
    name: d.name,
    objectName: d.objectName,
    url: d.url,
  }))

  emit('send', text, imageUrls, docMarkers, docFiles, props.quotedText)

  // Clear uploaded attachments after send
  cleanup()
  docAttachments.value = []

  if (hasQuote) emit('removeQuote')
}
</script>

<style lang="scss" scoped>
$primary: #4f46e5;
$surface: #fff;
$border: #e2e8f0;
$text-muted: #94a3b8;

.input-area {
  flex-shrink: 0;
  padding: 12px 24px 20px;
  background: $surface;

  .quote-bar {
    max-width: 768px;
    margin: 0 auto 8px;
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 6px 10px;
    background: #eef2ff;
    border: 1px solid rgba($primary, 0.2);
    border-radius: 8px;
    font-size: 13px;

    .quote-label {
      flex-shrink: 0;
      padding: 1px 6px;
      font-size: 11px;
      font-weight: 600;
      color: $primary;
      background: rgba($primary, 0.1);
      border-radius: 4px;
    }
    .quote-preview {
      flex: 1;
      color: #1e293b;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      line-height: 1.4;
    }
    .quote-close {
      flex-shrink: 0;
      color: $text-muted;
      &:hover {
        color: #dc2626;
      }
    }
  }

  .attach-preview-row {
    max-width: 768px;
    margin: 0 auto 8px;
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
  }

  .attach-thumb {
    position: relative;
    width: 56px;
    height: 56px;
    border-radius: 8px;
    overflow: hidden;
    border: 1px solid $border;
    background: #f8fafc;
    display: flex;
    align-items: center;
    justify-content: center;

    img {
      width: 100%;
      height: 100%;
      object-fit: cover;
    }

    &.uploading {
      opacity: 0.6;
    }
    &.failed {
      border-color: #fca5a5;
      background: #fef2f2;
    }

    .attach-spin {
      position: absolute;
      inset: 0;
      border: 2px solid #e2e8f0;
      border-top-color: $primary;
      border-radius: 50%;
      width: 20px;
      height: 20px;
      margin: auto;
      animation: spin 0.6s linear infinite;
    }
    .attach-fail-icon {
      font-size: 20px;
      color: #ef4444;
      font-weight: 700;
    }
    .attach-remove {
      position: absolute;
      top: 2px;
      right: 2px;
      width: 16px;
      height: 16px;
      border-radius: 50%;
      background: rgba(0, 0, 0, 0.45);
      color: #fff;
      font-size: 11px;
      line-height: 16px;
      text-align: center;
      cursor: pointer;
      opacity: 0;
      transition: opacity 0.15s;
    }
    &:hover .attach-remove {
      opacity: 1;
    }
  }

  .doc-attach {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 4px 10px;
    border-radius: 8px;
    border: 1px solid $border;
    background: #f8fafc;
    font-size: 12px;
    max-width: 260px;

    &.uploading {
      opacity: 0.6;
    }
    &.failed {
      border-color: #fca5a5;
      background: #fef2f2;
    }

    .doc-icon {
      font-size: 14px;
      color: $primary;
      flex-shrink: 0;
    }
    .doc-name {
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      color: #1e293b;
    }
    .doc-ok {
      color: #22c55e;
      font-size: 12px;
      flex-shrink: 0;
    }
    .attach-spin {
      width: 12px;
      height: 12px;
      flex-shrink: 0;
      border: 2px solid #e2e8f0;
      border-top-color: $primary;
      border-radius: 50%;
      animation: spin 0.6s linear infinite;
    }
    .attach-remove {
      flex-shrink: 0;
      width: 14px;
      height: 14px;
      border-radius: 50%;
      background: #e2e8f0;
      color: #64748b;
      font-size: 10px;
      line-height: 14px;
      text-align: center;
      cursor: pointer;
      &:hover {
        background: #fca5a5;
        color: #fff;
      }
    }
  }

  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }

  .model-row {
    max-width: 1024px;
    margin: 0 auto 8px;
    display: flex;
    flex-wrap: wrap;
    gap: 6px;

    .model-chip {
      font-size: 12px;
      padding: 3px 10px;
      border-radius: 12px;
      background: #f1f5f9;
      color: #64748b;
      cursor: pointer;
      transition: all 0.15s;
      &:hover {
        background: #e2e8f0;
      }
      &.active {
        background: $primary;
        color: #fff;
      }
    }
  }

  .input-inner {
    max-width: 1024px;
    margin: 0 auto;
    display: flex;
    align-items: flex-end;
    gap: 8px;
    background: #f8fafc;
    border: 1px solid $border;
    border-radius: 16px;
    padding: 8px 12px 8px 16px;
    transition:
      border-color 0.2s,
      box-shadow 0.2s;

    &:focus-within {
      border-color: $primary;
      box-shadow: 0 0 0 3px rgba($primary, 0.08);
    }

    textarea {
      flex: 1;
      min-height: 20px;
      max-height: 160px;
      overflow-y: auto;
      min-width: 0;
      border: none;
      outline: none;
      background: transparent;
      resize: none;
      padding: 7px 0;
      font-size: 14px;
      line-height: 1.5;
      font-family: inherit;
      color: #1e293b;

      &::placeholder {
        color: $text-muted;
      }
    }

    .input-actions {
      display: flex;
      align-items: center;
      gap: 4px;
      flex-shrink: 0;
    }

    .tool-btn {
      width: 36px;
      height: 36px;
      border-radius: 10px;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 0;
      color: $text-muted;
      border: none;
      font-size: 18px;
      transition:
        color 0.15s,
        background 0.15s;
      &:hover:not(:disabled) {
        color: $primary;
        background: rgba($primary, 0.06);
      }
      &:disabled {
        color: #d1d5db;
      }
    }

    .send-btn {
      width: 36px;
      height: 36px;
      border-radius: 10px;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 0;
      background: $primary;
      border: none;
      outline: none;
      &:hover:not(:disabled) {
        background: #4338ca;
      }
      &:disabled {
        background: #cbd5e1;
      }
      :deep(.anticon) {
        font-size: 15px;
      }
    }

    .abort-btn {
      width: 36px;
      height: 36px;
      border-radius: 10px;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 0;
      background: #dc2626;
      border: none;
      outline: none;
      &:hover {
        background: #b91c1c;
      }
      :deep(.anticon) {
        font-size: 15px;
      }
    }
  }
}
</style>
