<!-- MsgReferenceCard — DeepSeek-style search citation display -->
<template>
  <div v-if="references && references.length > 0" class="msg-refs mb-2">
    <!-- Header: click opens right-side ReferencePanel, chevron toggles inline expand -->
    <div class="refs-header" @click="emit('selectRefs', references)">
      <div class="refs-header-left">
        <svg
          class="refs-globe-icon"
          viewBox="0 0 24 24"
          width="14"
          height="14"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
        >
          <circle cx="12" cy="12" r="10" />
          <line x1="2" y1="12" x2="22" y2="12" />
          <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
        </svg>
        <span class="refs-label">
          搜索了 <strong>{{ references.length }}</strong> 个网页
        </span>
      </div>
      <svg
        class="refs-chevron"
        :class="{ rotated: expanded }"
        viewBox="0 0 24 24"
        width="12"
        height="12"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
        @click.stop="expanded = !expanded"
      >
        <path d="M6 9l6 6 6-6" />
      </svg>
    </div>

    <!-- Reference list -->
    <div v-show="expanded" class="refs-list">
      <template v-for="(ref, idx) in references" :key="idx">
        <div class="ref-item" :class="{ 'ref-expanded': openIdx === idx }">
          <div class="ref-item-header" @click="openIdx = openIdx === idx ? -1 : idx">
            <span class="ref-num">{{ idx + 1 }}</span>
            <div class="ref-item-main">
              <a
                class="ref-title"
                :href="ref.url"
                target="_blank"
                rel="noopener"
                @click.stop
                :title="ref.title || ref.url"
              >
                {{ ref.title || ref.domain || ref.url }}
              </a>
              <span v-if="ref.domain" class="ref-domain">{{ ref.domain }}</span>
            </div>
            <svg
              class="ref-item-chevron"
              :class="{ rotated: openIdx === idx }"
              viewBox="0 0 24 24"
              width="12"
              height="12"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
            >
              <path d="M6 9l6 6 6-6" />
            </svg>
          </div>
          <div v-if="openIdx === idx && ref.snippet" class="ref-snippet">{{ ref.snippet }}</div>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

defineProps<{
  references?: Array<{ title?: string; url: string; snippet?: string; domain?: string }>
}>()

const emit = defineEmits<{
  selectRefs: [refs: Array<{ title?: string; url: string; snippet?: string; domain?: string }>]
}>()

const expanded = ref(false)
const openIdx = ref(-1)
</script>

<style lang="scss" scoped>
.msg-refs {
  margin: 8px 0 12px 0;
  padding: 0;
  border-radius: 10px;
  background: #fafafa;
  border: 1px solid #f0f0f0;
  overflow: hidden;
}

.refs-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  cursor: pointer;
  user-select: none;
  transition: background 0.12s;

  &:hover {
    background: #f5f5f5;
  }
}

.refs-header-left {
  display: flex;
  align-items: center;
  gap: 6px;
}

.refs-globe-icon {
  color: #8b8b8b;
  flex-shrink: 0;
}

.refs-label {
  font-size: 12.5px;
  color: #555;

  strong {
    font-weight: 600;
    color: #4f46e5;
  }
}

.refs-chevron {
  color: #bbb;
  flex-shrink: 0;
  transition: transform 0.2s ease;

  &.rotated {
    transform: rotate(180deg);
  }
}

.refs-list {
  border-top: 1px solid #f0f0f0;
}

.ref-item {
  border-bottom: 1px solid #f5f5f5;

  &:last-child {
    border-bottom: none;
  }
}

.ref-item-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 7px 12px;
  cursor: pointer;
  user-select: none;
  transition: background 0.1s;

  &:hover {
    background: #f8f8f8;
  }
}

.ref-num {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: #eef2ff;
  color: #4f46e5;
  font-size: 10px;
  font-weight: 600;
  flex-shrink: 0;
}

.ref-item-main {
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 6px;
}

.ref-title {
  font-size: 12px;
  color: #374151;
  text-decoration: none;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 320px;
  transition: color 0.12s;
  line-height: 1.4;

  &:hover {
    color: #4f46e5;
    text-decoration: underline;
  }
}

.ref-domain {
  display: inline-block;
  font-size: 10px;
  color: #9ca3af;
  background: #f3f4f6;
  border-radius: 4px;
  padding: 1px 5px;
  white-space: nowrap;
  flex-shrink: 0;
}

.ref-item-chevron {
  color: #ccc;
  flex-shrink: 0;
  transition: transform 0.2s ease;

  &.rotated {
    transform: rotate(180deg);
  }
}

.ref-snippet {
  padding: 0 12px 8px 38px;
  font-size: 11.5px;
  color: #6b7280;
  line-height: 1.55;
  white-space: pre-wrap;
  word-break: break-word;
}
</style>
