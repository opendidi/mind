<!-- Outline search input -->
<template>
  <div class="outline-search">
    <SearchOutlined class="search-icon" />
    <input
      ref="inputRef"
      :value="modelValue"
      class="search-input"
      placeholder="搜索标题…"
      @input="$emit('update:modelValue', ($event.target as HTMLInputElement).value)"
      @keydown="onKeydown"
    />
    <template v-if="modelValue">
      <span class="search-clear" @click="$emit('update:modelValue', '')">✕</span>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { SearchOutlined } from '@ant-design/icons-vue'

defineProps<{
  modelValue: string
}>()

const emit = defineEmits<{
  'update:modelValue': [value: string]
  esc: []
}>()

const inputRef = ref<HTMLInputElement>()

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Escape') {
    emit('esc')
  }
}

defineExpose({ inputRef })
</script>

<style lang="scss" scoped>
.outline-search {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  border-bottom: 1px solid var(--color-border, #e2e8f0);
  flex-shrink: 0;

  .search-icon {
    color: var(--color-text-muted, #94a3b8);
    font-size: 13px;
    flex-shrink: 0;
  }

  .search-input {
    flex: 1;
    border: none;
    outline: none;
    font-size: 12.5px;
    background: transparent;
    color: var(--color-text, #1e293b);
    min-width: 0;

    &::placeholder {
      color: var(--color-text-muted, #94a3b8);
    }
  }

  .search-clear {
    cursor: pointer;
    color: var(--color-text-muted, #94a3b8);
    font-size: 12px;
    padding: 2px 4px;
    flex-shrink: 0;

    &:hover {
      color: var(--color-text, #1e293b);
    }
  }
}
</style>
