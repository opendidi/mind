<template>
  <div class="msg-item" :class="`msg-${message.role}`">
    <!-- User message -->
    <div v-if="message.role === 'user'" class="msg-user">
      <div class="msg-bubble user-bubble">
        {{ message.content }}
      </div>
    </div>

    <!-- Assistant message -->
    <div v-else-if="message.role === 'assistant'" class="msg-assistant">
      <!-- Thinking -->
      <ThinkCard v-if="message.thinking" :content="message.thinking" />

      <!-- Tool calls (grouped for canvas) -->
      <div v-if="message.toolCalls?.length" class="tool-calls-block">
        <template v-for="item in groupedCalls" :key="Array.isArray(item) ? item[0].id : item.id">
          <AgentToolGroupCard v-if="Array.isArray(item) && item.length > 1" :tool-calls="item" />
          <AgentToolCard v-else :tool-call="Array.isArray(item) ? item[0] : item" />
        </template>
      </div>

      <!-- Map / Route cards + text from content -->
      <template v-if="message.content">
        <template v-for="(part, pi) in contentParts" :key="pi">
          <MapCard
            v-if="part.type === 'map'"
            :title="part.data.title"
            :center="part.data.center"
            :zoom="part.data.zoom"
            :markers="part.data.markers"
          />
          <RouteCard
            v-else-if="part.type === 'route'"
            :mode="part.data.mode"
            :from="part.data.from"
            :to="part.data.to"
          />
          <div v-else class="msg-bubble assistant-bubble" v-html="part.html"></div>
        </template>
      </template>

      <!-- TTS Action Row (speaker button below message) -->
      <div v-if="showSpeaker" class="msg-actions">
        <button
          class="speaker-btn"
          :class="{ loading: ttsLoading, playing: ttsSpeaking }"
          :title="speakerTooltip"
          @click="onSpeakerClick"
        >
          <span v-if="ttsLoading" class="spinner"></span>
          <span v-else-if="ttsSpeaking">⏹</span>
          <span v-else>🔊</span>
          <span class="speaker-label">{{ speakerLabel }}</span>
        </button>
      </div>
    </div>

    <!-- System message -->
    <div v-else class="msg-system">
      <span>{{ message.content }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { ChatMessage, ToolCallRecord } from './AgentStreamHandler'
import { sanitizeHtml } from '@/utils/sanitize'
import { useSpeech } from '@/composables/useSpeech'
import ThinkCard from '@/components/chat/ThinkCard.vue'
import AgentToolCard from './AgentToolCard.vue'
import AgentToolGroupCard from './AgentToolGroupCard.vue'
import MapCard from '@/components/shared/MapCard.vue'
import RouteCard from '@/components/shared/RouteCard.vue'

const props = defineProps<{
  message: ChatMessage
}>()

const { speaking: ttsSpeaking, loading: ttsLoading, speakChatTTS, stop } = useSpeech()

// ── show speaker only for completed assistant messages with content ──────

const showSpeaker = computed(() => {
  if (props.message.role !== 'assistant') return false
  const text = props.message.content
  if (!text || text.trim().length < 2) return false
  // Don't show if message is still streaming (check for streaming flag)
  if ((props.message as any).streaming) return false
  return true
})

const speakerLabel = computed(() => {
  if (ttsLoading.value) return '生成中...'
  if (ttsSpeaking.value) return '停止'
  return '朗读'
})

const speakerTooltip = computed(() => {
  if (ttsLoading.value) return 'ChatTTS 正在生成语音...'
  if (ttsSpeaking.value) return '停止播放'
  return 'ChatTTS 朗读此消息'
})

function onSpeakerClick() {
  if (ttsLoading.value) return // do nothing while loading
  if (ttsSpeaking.value) {
    stop()
    return
  }
  speakChatTTS(props.message.content)
}

// ── content parsing ──────────────────────────────────────────────────────

interface ContentPart {
  type: 'text' | 'map' | 'route'
  html?: string
  data?: Record<string, unknown>
}

const contentParts = computed<ContentPart[]>(() => {
  const text = props.message.content
  if (!text) return []

  const parts: ContentPart[] = []

  // Match ```map or ```route blocks, extract JSON content
  const combinedRegex = /```(map|route)\s*\n([\s\S]*?)```/g
  let lastIndex = 0
  let match: RegExpExecArray | null

  while ((match = combinedRegex.exec(text)) !== null) {
    // Text before this match
    if (match.index > lastIndex) {
      const before = text.slice(lastIndex, match.index).trim()
      if (before) {
        parts.push({ type: 'text', html: renderContent(before) })
      }
    }

    const blockType = match[1]
    const blockContent = match[2].trim()

    try {
      const data = JSON.parse(blockContent)
      if (blockType === 'map') {
        parts.push({ type: 'map', data })
      } else {
        parts.push({ type: 'route', data })
      }
    } catch {
      // Invalid JSON — render as code block
      parts.push({ type: 'text', html: renderContent(`\`\`\`${blockType}\n${blockContent}\n\`\`\``) })
    }

    lastIndex = match.index + match[0].length
  }

  // Remaining text after last match
  if (lastIndex < text.length) {
    const after = text.slice(lastIndex).trim()
    if (after) {
      parts.push({ type: 'text', html: renderContent(after) })
    }
  }

  return parts
})

const groupedCalls = computed(() => {
  const tcs = props.message.toolCalls
  if (!tcs || tcs.length === 0) return []
  const groups: Array<ToolCallRecord | ToolCallRecord[]> = []
  let canvasGroup: ToolCallRecord[] = []
  for (const tc of tcs) {
    if (tc.tool === 'canvas' || tc.tool.startsWith('canvas_')) {
      canvasGroup.push(tc)
    } else {
      if (canvasGroup.length > 0) {
        groups.push([...canvasGroup])
        canvasGroup = []
      }
      groups.push(tc)
    }
  }
  if (canvasGroup.length > 0) groups.push([...canvasGroup])
  return groups
})

function renderContent(text: string): string {
  const html = text
    .replace(/```(\w*)\n?([^`]+)```/g, '<pre><code>$2</code></pre>')
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\n/g, '<br>')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
  return sanitizeHtml(html)
}
</script>

<style scoped lang="less">
.msg-item {
  display: flex;
  flex-direction: column;
}

.msg-user {
  display: flex;
  justify-content: flex-end;

  .user-bubble {
    background: #1677ff;
    color: #fff;
    border-radius: 12px 12px 4px 12px;
  }
}

.msg-assistant {
  display: flex;
  flex-direction: column;
  gap: 8px;

  .assistant-bubble {
    background: #fff;
    border-radius: 12px 12px 12px 4px;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
  }
}

.msg-system {
  text-align: center;
  font-size: 12px;
  color: #aaa;
  padding: 4px 0;
}

.msg-bubble {
  max-width: 85%;
  padding: 10px 14px;
  font-size: 14px;
  line-height: 1.6;
  word-break: break-word;

  :deep(pre) {
    background: #f5f5f5;
    border-radius: 4px;
    padding: 8px 12px;
    margin: 6px 0;
    overflow-x: auto;
    font-size: 13px;
  }

  :deep(code) {
    background: rgba(0, 0, 0, 0.06);
    padding: 1px 4px;
    border-radius: 3px;
    font-size: 13px;
  }

  :deep(pre code) {
    background: none;
    padding: 0;
  }
}

.tool-calls-block {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

// ── TTS Speaker Button ───────────────────────────────────────────────────

.msg-actions {
  display: flex;
  align-items: center;
  gap: 4px;
  padding-left: 4px;
}

.speaker-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 10px;
  border: 1px solid #e8e8e8;
  border-radius: 14px;
  background: #fafafa;
  color: #888;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s ease;
  outline: none;

  &:hover {
    background: #f0f5ff;
    border-color: #1677ff;
    color: #1677ff;
  }

  &.loading {
    color: #fa8c16;
    border-color: #ffd591;
    background: #fffbe6;
    cursor: not-allowed;
  }

  &.playing {
    color: #1677ff;
    border-color: #91caff;
    background: #f0f5ff;
  }

  .speaker-label {
    font-size: 11px;
  }
}

// tiny css spinner for loading state
.spinner {
  display: inline-block;
  width: 12px;
  height: 12px;
  border: 2px solid #ffd591;
  border-top-color: #fa8c16;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
