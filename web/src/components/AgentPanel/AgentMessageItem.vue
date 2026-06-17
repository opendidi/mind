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
      <AgentThinkCard
        v-if="message.thinking"
        :content="message.thinking"
      />

      <!-- Tool calls (grouped for canvas) -->
      <div v-if="message.toolCalls?.length" class="tool-calls-block">
        <template v-for="item in groupedCalls" :key="Array.isArray(item) ? item[0].id : item.id">
          <AgentToolGroupCard
            v-if="Array.isArray(item) && item.length > 1"
            :tool-calls="item"
          />
          <AgentToolCard
            v-else
            :tool-call="Array.isArray(item) ? item[0] : item"
          />
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
    </div>

    <!-- System message -->
    <div v-else class="msg-system">
      <span>{{ message.content }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type { ChatMessage, ToolCallRecord } from './AgentStreamHandler';
import AgentThinkCard from './AgentThinkCard.vue';
import AgentToolCard from './AgentToolCard.vue';
import AgentToolGroupCard from './AgentToolGroupCard.vue';
import MapCard from './MapCard.vue';
import RouteCard from './RouteCard.vue';

const props = defineProps<{
  message: ChatMessage;
}>();

interface ContentPart {
  type: 'text' | 'map' | 'route';
  html?: string;
  data?: any;
}

const contentParts = computed<ContentPart[]>(() => {
  const text = props.message.content;
  if (!text) return [];

  const parts: ContentPart[] = [];

  // Match ```map or ```route blocks, extract JSON content
  const combinedRegex = /```(map|route)\s*\n([\s\S]*?)```/g;
  let lastIndex = 0;
  let match: RegExpExecArray | null;

  while ((match = combinedRegex.exec(text)) !== null) {
    // Text before this match
    if (match.index > lastIndex) {
      const before = text.slice(lastIndex, match.index).trim();
      if (before) {
        parts.push({ type: 'text', html: renderContent(before) });
      }
    }

    const blockType = match[1];
    const blockContent = match[2].trim();

    try {
      const data = JSON.parse(blockContent);
      if (blockType === 'map') {
        parts.push({ type: 'map', data });
      } else {
        parts.push({ type: 'route', data });
      }
    } catch {
      // Invalid JSON — render as code block
      parts.push({ type: 'text', html: renderContent(`\`\`\`${blockType}\n${blockContent}\n\`\`\``) });
    }

    lastIndex = match.index + match[0].length;
  }

  // Remaining text after last match
  if (lastIndex < text.length) {
    const after = text.slice(lastIndex).trim();
    if (after) {
      parts.push({ type: 'text', html: renderContent(after) });
    }
  }

  return parts;
});

const groupedCalls = computed(() => {
  const tcs = props.message.toolCalls;
  if (!tcs || tcs.length === 0) return [];
  const groups: Array<ToolCallRecord | ToolCallRecord[]> = [];
  let canvasGroup: ToolCallRecord[] = [];
  for (const tc of tcs) {
    if (tc.tool === 'canvas' || tc.tool.startsWith('canvas_')) {
      canvasGroup.push(tc);
    } else {
      if (canvasGroup.length > 0) { groups.push([...canvasGroup]); canvasGroup = []; }
      groups.push(tc);
    }
  }
  if (canvasGroup.length > 0) groups.push([...canvasGroup]);
  return groups;
});

function renderContent(text: string): string {
  // Simple markdown: code blocks and line breaks
  return text
    .replace(/```(\w*)\n?([^`]+)```/g, '<pre><code>$2</code></pre>')
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\n/g, '<br>')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
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
    box-shadow: 0 1px 3px rgba(0,0,0,0.08);
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
    background: rgba(0,0,0,0.06);
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
</style>
