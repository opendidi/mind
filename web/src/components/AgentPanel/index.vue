<template>
  <a-drawer
    v-model:visible="visible"
    title="AI 助手"
    placement="right"
    :width="420"
    :closable="true"
    :body-style="{ padding: 0, height: 'calc(100% - 55px)' }"
    @close="handleClose"
  >
    <div class="agent-panel">
      <!-- Error banner -->
      <template v-if="stream.state.error">
        <div class="agent-error">
          <span>{{ stream.state.error }}</span>
          <a-button size="small" type="link" @click="stream.state.error = null">
            ✕
          </a-button>
        </div>
      </template>

      <!-- Messages -->
      <div ref="msgListRef" class="agent-messages">
        <template v-for="msg in stream.state.messages" :key="msg.id">
          <AgentMessageItem :message="msg" />
        </template>

        <template v-if="stream.state.loading">
          <div class="agent-typing">
            <span class="typing-dot"></span>
            <span class="typing-dot"></span>
            <span class="typing-dot"></span>
          </div>
        </template>
      </div>

      <!-- Input -->
      <div class="agent-input-wrap">
        <AgentInput :disabled="stream.state.loading" :initial-value="presetInput" @send="handleSend" />
      </div>
    </div>
  </a-drawer>
</template>

<script setup lang="ts">
import { ref, watch, nextTick, onUnmounted } from "vue";
import { AgentStreamHandler } from "./AgentStreamHandler";
import AgentMessageItem from "./AgentMessageItem.vue";
import AgentInput from "./AgentInput.vue";
import { executeCanvasTool } from "@/utils/canvasBridge";
import { useSelection } from "@/services/selections";

const visible = ref(false);
const msgListRef = ref<HTMLElement>();
const stream = new AgentStreamHandler();

// Wire tool results to Meta2D canvas operations
stream.onToolResult((tool, args, success, result) => {
  executeCanvasTool(tool, args, success, result);
});

// Auto-scroll to bottom on new messages or tool calls
watch(
  () => [stream.state.messages.length, stream.state.toolCalls.length],
  () => {
    nextTick(() => {
      if (msgListRef.value) {
        msgListRef.value.scrollTop = msgListRef.value.scrollHeight;
      }
    });
  }
);

function handleSend(text: string, images?: string[]) {
  stream.send(text, images);
}

function handleClose() {
  stream.abort();
}

onUnmounted(() => {
  stream.abort();
});

let presetInput = '';
const { selections } = useSelection();

// Auto-inject pen selection context when drawer is open
watch(
  () => selections.pen,
  (pen) => {
    if (!visible.value || !pen) return;
    presetInput = `请帮我分析这个节点: ID=${pen.id}, 类型=${pen.name || 'unknown'}, 文字="${(pen.text || '').slice(0, 100)}", 位置=(${pen.x}, ${pen.y}), 大小=${pen.width}x${pen.height}`;
  },
);

function open(context?: string) {
  visible.value = true;
  if (context) {
    presetInput = context;
  }
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

.agent-typing {
  display: flex;
  gap: 4px;
  padding: 12px 16px;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
  align-self: flex-start;

  .typing-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #bbb;
    animation: typing-bounce 1.4s infinite both;

    &:nth-child(2) {
      animation-delay: 0.2s;
    }
    &:nth-child(3) {
      animation-delay: 0.4s;
    }
  }
}

@keyframes typing-bounce {
  0%,
  60%,
  100% {
    transform: translateY(0);
  }
  30% {
    transform: translateY(-4px);
  }
}

.agent-input-wrap {
  border-top: 1px solid #e8e8e8;
  padding: 12px 16px;
  background: #fff;
}
</style>