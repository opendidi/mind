<template>
  <a-drawer
    v-model:open="visible"
    title="AI 助手"
    placement="right"
    :width="420"
    :closable="true"
    :body-style="{ padding: 0, height: 'calc(100% - 55px)' }"
    @close="handleClose"
  >
    <div class="agent-panel">
      <!-- Error banner -->
      <div v-if="stream.state.error" class="agent-error">
        <span>{{ stream.state.error }}</span>
        <a-button size="small" type="link" @click="stream.state.error = null">✕</a-button>
      </div>

      <!-- Messages -->
      <div ref="msgListRef" class="agent-messages">
        <div v-if="stream.state.messages.length === 0" class="agent-welcome">
          <div class="welcome-icon">🤖</div>
          <h3>你好，我是小M</h3>
          <p>你的图形编辑助手。可以帮你：</p>
          <ul>
            <li>🎨 创建和编辑图形</li>
            <li>📋 管理蓝图</li>
            <li>🧠 生成思维导图</li>
            <li>📐 自动布局排版</li>
          </ul>
        </div>

        <!-- Plan card -->
        <AgentPlanCard
          v-if="stream.state.plan"
          :plan="stream.state.plan"
        />

        <!-- Messages -->
        <div
          v-for="msg in stream.state.messages"
          :key="msg.id"
        >
          <AgentMessageItem :message="msg" />
        </div>

        <!-- Loading indicator -->
        <div v-if="stream.state.loading && !currentAssistantContent" class="agent-typing">
          <span class="typing-dot"></span>
          <span class="typing-dot"></span>
          <span class="typing-dot"></span>
        </div>
      </div>

      <!-- Input -->
      <div class="agent-input-wrap">
        <AgentInput
          :disabled="stream.state.loading"
          @send="handleSend"
        />
      </div>
    </div>
  </a-drawer>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick, onUnmounted } from 'vue';
import { AgentStreamHandler } from './AgentStreamHandler';
import AgentMessageItem from './AgentMessageItem.vue';
import AgentPlanCard from './AgentPlanCard.vue';
import AgentInput from './AgentInput.vue';

const visible = ref(false);
const msgListRef = ref<HTMLElement>();
const stream = ref(new AgentStreamHandler());

const currentAssistantContent = computed(() => {
  const msgs = stream.value.state.messages;
  const last = msgs[msgs.length - 1];
  return last?.role === 'assistant' && stream.value.state.loading ? last.content : '';
});

// Auto-scroll to bottom on new messages
watch(
  () => stream.value.state.messages.length,
  () => {
    nextTick(() => {
      if (msgListRef.value) {
        msgListRef.value.scrollTop = msgListRef.value.scrollHeight;
      }
    });
  },
);

watch(
  () => stream.value.state.toolCalls.length,
  () => {
    nextTick(() => {
      if (msgListRef.value) {
        msgListRef.value.scrollTop = msgListRef.value.scrollHeight;
      }
    });
  },
);

function handleSend(text: string) {
  stream.value.send(text);
}

function handleClose() {
  stream.value.abort();
}

// Cleanup SSE on component unmount
onUnmounted(() => {
  stream.value.abort();
});

function open() {
  visible.value = true;
}

function close() {
  visible.value = false;
}

defineExpose({ open, close, visible });
</script>

<style scoped lang="less">
.agent-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #fafafa;
}

.agent-error {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 16px;
  background: #fff2f0;
  border-bottom: 1px solid #ffccc7;
  color: #ff4d4f;
  font-size: 13px;
}

.agent-messages {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.agent-welcome {
  text-align: center;
  padding: 40px 20px;
  color: #888;

  .welcome-icon {
    font-size: 48px;
    margin-bottom: 12px;
  }

  h3 {
    margin: 0 0 8px;
    font-size: 18px;
    color: #333;
  }

  p {
    margin: 0 0 12px;
  }

  ul {
    list-style: none;
    padding: 0;
    margin: 0;
    text-align: left;
    display: inline-block;

    li {
      padding: 4px 0;
      font-size: 14px;
    }
  }
}

.agent-typing {
  display: flex;
  gap: 4px;
  padding: 12px 16px;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.08);
  align-self: flex-start;

  .typing-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #bbb;
    animation: typing-bounce 1.4s infinite both;

    &:nth-child(2) { animation-delay: 0.2s; }
    &:nth-child(3) { animation-delay: 0.4s; }
  }
}

@keyframes typing-bounce {
  0%, 60%, 100% { transform: translateY(0); }
  30% { transform: translateY(-4px); }
}

.agent-input-wrap {
  border-top: 1px solid #e8e8e8;
  padding: 12px 16px;
  background: #fff;
}
</style>
