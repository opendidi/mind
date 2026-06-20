<!-- MsgReferenceCard — DeepSeek-style reference display below AI replies -->
<template>
  <div v-if="references && references.length > 0" class="msg-refs">
    <div class="refs-header" @click="$emit('selectRefs', references)">
      <!-- Globe icon -->
      <svg class="refs-globe-icon" viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="12" cy="12" r="10" />
        <line x1="2" y1="12" x2="22" y2="12" />
        <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
      </svg>
      <span class="refs-label">阅读了 <strong>{{ references.length }}</strong> 个网页</span>
      <svg class="refs-chevron" viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M9 18l6-6-6-6" />
      </svg>
    </div>
    <!-- Inline reference titles (compact) -->
    <div class="refs-list">
      <template v-for="(ref, idx) in references.slice(0, 3)" :key="idx">
        <span class="refs-divider" v-if="idx > 0">·</span>
        <a
          class="refs-link"
          :href="ref.url"
          target="_blank"
          rel="noopener"
          :title="ref.title || ref.url"
          @click.stop
        >
          {{ idx + 1 }}. {{ ref.title || ref.domain || ref.url }}
        </a>
      </template>
      <span v-if="references.length > 3" class="refs-more">
        · 等{{ references.length }}条
      </span>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  references?: Array<{ title?: string; url: string; snippet?: string; domain?: string }>;
}>();

defineEmits<{
  selectRefs: [refs: Array<{ title?: string; url: string; snippet?: string; domain?: string }>];
}>();
</script>

<style lang="scss" scoped>
.msg-refs {
  margin-top: 6px;
  padding: 8px 12px;
  border-radius: 8px;
  background: #fafafa;
  border: 1px solid #f0f0f0;
}

.refs-header {
  display: flex;
  align-items: center;
  gap: 5px;
  cursor: pointer;
  user-select: none;
  padding: 2px 0;
  border-radius: 4px;
  transition: background 0.12s;

  &:hover {
    background: #f5f5f5;
    margin: 0 -6px;
    padding-left: 6px;
    padding-right: 6px;
  }

  .refs-globe-icon {
    color: #8b8b8b;
    flex-shrink: 0;
  }

  .refs-label {
    font-size: 12px;
    color: #666;

    strong {
      font-weight: 600;
      color: #4f46e5;
    }
  }

  .refs-chevron {
    color: #bbb;
    flex-shrink: 0;
    margin-left: 2px;
  }
}

.refs-list {
  margin-top: 6px;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 2px;
  font-size: 11.5px;
  line-height: 1.6;
}

.refs-divider {
  color: #d4d4d4;
  margin: 0 3px;
  user-select: none;
}

.refs-link {
  color: #6b7280;
  text-decoration: none;
  max-width: 260px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  transition: color 0.12s;

  &:hover {
    color: #4f46e5;
    text-decoration: underline;
  }
}

.refs-more {
  color: #aaa;
  font-size: 11px;
  white-space: nowrap;
}
</style>
