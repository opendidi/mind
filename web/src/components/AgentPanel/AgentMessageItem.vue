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

      <!-- Tool calls -->
      <div v-if="message.toolCalls?.length" class="tool-calls-block">
        <AgentToolCard
          v-for="tc in message.toolCalls"
          :key="tc.id"
          :tool-call="tc"
        />
      </div>

      <!-- Text content -->
      <div v-if="message.content" class="msg-bubble assistant-bubble">
        <div v-html="renderContent(message.content)"></div>
      </div>
    </div>

    <!-- System message -->
    <div v-else class="msg-system">
      <span>{{ message.content }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { ChatMessage } from './AgentStreamHandler';
import AgentThinkCard from './AgentThinkCard.vue';
import AgentToolCard from './AgentToolCard.vue';

defineProps<{
  message: ChatMessage;
}>();

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
