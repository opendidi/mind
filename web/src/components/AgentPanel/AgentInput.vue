<template>
  <div class="agent-input" :class="{ focused }">
    <textarea
      ref="textareaRef"
      v-model="inputText"
      :disabled="disabled"
      rows="1"
      placeholder="输入消息，Enter 发送，Shift+Enter 换行..."
      @keydown="handleEnter"
      @focus="focused = true"
      @blur="focused = false"
    />
    <button
      class="send-btn"
      :disabled="disabled || !inputText.trim()"
      @click="handleSend"
    >
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
</template>

<script setup lang="ts">
import { ref, watch, nextTick } from "vue";

const props = defineProps<{
  disabled: boolean;
  initialValue?: string;
}>();

const emit = defineEmits<{
  send: [text: string];
}>();

const inputText = ref("");
const textareaRef = ref<HTMLTextAreaElement>();
const focused = ref(false);

// Apply preset context on mount
watch(
  () => props.initialValue,
  (val) => {
    if (val) {
      inputText.value = val;
      nextTick(autoResize);
    }
  },
  { immediate: true },
);

function autoResize() {
  const el = textareaRef.value;
  if (!el) return;
  el.style.height = "auto";
  el.style.height = el.scrollHeight + "px";
}

watch(inputText, () => nextTick(autoResize), { flush: "post" });

function handleSend() {
  const text = inputText.value.trim();
  if (!text || props.disabled) return;
  emit("send", text);
  inputText.value = "";
}

function handleEnter(e: KeyboardEvent) {
  if (e.key !== "Enter") return;
  if (e.shiftKey) return;
  e.preventDefault();
  handleSend();
}
</script>

<style scoped lang="less">
.agent-input {
  display: flex;
  align-items: flex-end;
  gap: 6px;
  padding: 6px 6px 6px 14px;
  border: 1px solid #e0e0e0;
  border-radius: 12px;
  background: #fff;
  transition: border-color 0.2s, box-shadow 0.2s;

  &.focused {
    border-color: #1677ff;
    box-shadow: 0 0 0 2px rgba(22, 119, 255, 0.12);
  }

  textarea {
    flex: 1;
    border: none;
    outline: none;
    resize: none;
    font-size: 14px;
    line-height: 1.5;
    font-family: inherit;
    padding: 4px 0;
    background: transparent;
    color: #333;
    max-height: 160px;
    overflow-y: auto;

    &::placeholder {
      color: #bfbfbf;
    }

    &:disabled {
      color: #999;
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
    transition: background 0.2s, opacity 0.2s;

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