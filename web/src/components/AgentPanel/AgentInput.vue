<template>
  <div class="agent-input">
    <a-textarea
      v-model:value="inputText"
      :disabled="disabled"
      :auto-size="{ minRows: 1, maxRows: 4 }"
      placeholder="输入消息，Enter 发送，Shift+Enter 换行..."
      @pressEnter="handleEnter"
    />
    <a-button
      type="primary"
      :disabled="disabled || !inputText.trim()"
      :loading="disabled"
      @click="handleSend"
    >
      发送
    </a-button>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';

const props = defineProps<{
  disabled: boolean;
}>();

const emit = defineEmits<{
  send: [text: string];
}>();

const inputText = ref('');

function handleSend() {
  const text = inputText.value.trim();
  if (!text || props.disabled) return;
  emit('send', text);
  inputText.value = '';
}

function handleEnter(e: KeyboardEvent) {
  if (e.shiftKey) return; // Allow Shift+Enter for newline
  e.preventDefault();
  handleSend();
}
</script>

<style scoped lang="less">
.agent-input {
  display: flex;
  gap: 8px;
  align-items: flex-end;

  :deep(.ant-input) {
    resize: none;
    font-size: 14px;
  }

  .ant-btn {
    flex-shrink: 0;
  }
}
</style>
