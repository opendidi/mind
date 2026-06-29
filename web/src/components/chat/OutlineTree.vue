<!-- Outline tree — recursive heading groups with search highlight -->
<template>
  <div class="outline-tree">
    <template v-for="group in filteredGroups" :key="group.msgId">
      <!-- Group header -->
      <div class="outline-group-header" @click="$emit('toggleGroup', group.msgId)">
        <svg
          class="group-chevron"
          :class="{ collapsed: collapsedGroups.has(group.msgId) }"
          viewBox="0 0 24 24"
          width="10"
          height="10"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
        >
          <path d="M6 9l6 6 6-6" />
        </svg>
        <span class="group-label">AI 回复 #{{ group.msgIndex }}</span>
      </div>

      <!-- Group headings -->
      <template v-if="!collapsedGroups.has(group.msgId)">
        <div
          v-for="item in flattenItems(group.headings)"
          :key="item.heading.id"
          class="outline-item"
          :class="{
            active: item.heading.id === activeId,
            'has-match': searchQuery && item.matched,
          }"
          :style="{ paddingLeft: 8 + item.heading.level * 12 + 'px' }"
          @click="$emit('select', item.heading)"
        >
          <span class="item-bullet" :class="'h' + item.heading.level">H{{ item.heading.level }}</span>
          <span class="item-text" v-html="highlightText(item.heading.text, searchQuery)" />
        </div>
      </template>
    </template>

    <!-- Empty state -->
    <template v-if="filteredGroups.length === 0 && !searchQuery">
      <div class="outline-empty">
        <span class="empty-icon">📑</span>
        <span class="empty-title">暂无标题</span>
        <span class="empty-desc">AI 回复中的标题将在这里显示</span>
      </div>
    </template>
    <template v-else-if="filteredGroups.length === 0 && searchQuery">
      <div class="outline-empty">
        <span class="empty-desc">未找到匹配的标题</span>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import type { Heading, OutlineGroup } from '@/composables/useOutline'

const props = defineProps<{
  filteredGroups: OutlineGroup[]
  collapsedGroups: Set<string>
  activeId: string | null
  searchQuery: string
}>()

defineEmits<{
  toggleGroup: [msgId: string]
  select: [heading: Heading]
}>()

interface FlattenedItem {
  heading: Heading
  matched: boolean
}

/** Flatten heading tree for rendering, marking search matches */
function flattenItems(headings: Heading[]): FlattenedItem[] {
  const q = props.searchQuery.trim().toLowerCase()
  const result: FlattenedItem[] = []

  function walk(list: Heading[]) {
    for (const h of list) {
      result.push({
        heading: h,
        matched: q ? h.text.toLowerCase().includes(q) : false,
      })
      if (h.children.length > 0) walk(h.children)
    }
  }

  walk(headings)
  return result
}

/** Highlight matching text */
function highlightText(text: string, query: string): string {
  if (!query.trim()) return escapeHtml(text)
  const q = query.trim()
  const escaped = escapeHtml(text)
  const regex = new RegExp(`(${escapeRegex(q)})`, 'gi')
  return escaped.replace(regex, '<mark class="outline-mark">$1</mark>')
}

function escapeHtml(s: string): string {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
}

function escapeRegex(s: string): string {
  return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}
</script>

<style lang="scss" scoped>
.outline-tree {
  flex: 1;
  overflow-y: auto;
  padding: 4px 0;

  &::-webkit-scrollbar {
    width: 4px;
  }

  &::-webkit-scrollbar-track {
    background: transparent;
  }

  &::-webkit-scrollbar-thumb {
    background: transparent;
    border-radius: 2px;
  }

  &:hover::-webkit-scrollbar-thumb {
    background: #d1d5db;
  }
}

.outline-group-header {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 5px 12px;
  cursor: pointer;
  user-select: none;
  transition: background 0.1s;

  &:hover {
    background: var(--color-hover, #f1f5f9);
  }

  .group-chevron {
    color: var(--color-text-muted, #94a3b8);
    flex-shrink: 0;
    transition: transform 0.15s;

    &.collapsed {
      transform: rotate(-90deg);
    }
  }

  .group-label {
    font-size: 11px;
    font-weight: 600;
    color: var(--color-text-muted, #94a3b8);
    text-transform: uppercase;
    letter-spacing: 0.3px;
  }
}

.outline-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 3px 12px;
  cursor: pointer;
  user-select: none;
  transition: background 0.1s;
  border-left: 2px solid transparent;

  &:hover {
    background: var(--color-hover, #f1f5f9);
  }

  &.active {
    background: rgba(79, 70, 229, 0.06);
    border-left-color: #4f46e5;

    .item-text {
      color: #4f46e5;
      font-weight: 600;
    }
  }

  .item-bullet {
    font-size: 9px;
    font-weight: 700;
    color: var(--color-text-muted, #94a3b8);
    flex-shrink: 0;
    min-width: 18px;
    text-align: right;
    opacity: 0.6;

    &.h1 { opacity: 1; color: #1e293b; }
    &.h2 { opacity: 0.85; }
  }

  .item-text {
    font-size: 12.5px;
    line-height: 1.4;
    color: var(--color-text, #1e293b);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;

    :deep(.outline-mark) {
      background: #fef08a;
      color: #854d0e;
      border-radius: 2px;
      padding: 0 1px;
    }
  }

  &.has-match .item-text {
    font-weight: 500;
  }
}

.outline-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 32px 16px;
  gap: 6px;

  .empty-icon {
    font-size: 28px;
    margin-bottom: 4px;
  }

  .empty-title {
    font-size: 13px;
    font-weight: 600;
    color: var(--color-text-secondary, #64748b);
  }

  .empty-desc {
    font-size: 12px;
    color: var(--color-text-muted, #94a3b8);
    text-align: center;
  }
}
</style>
