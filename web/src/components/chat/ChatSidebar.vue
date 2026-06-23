<!-- Chat sidebar — conversation list + search + actions -->
<template>
  <aside class="chat-sidebar" :class="{ collapsed }">
    <div class="sidebar-header">
      <router-link to="/" class="sidebar-logo">
        <i class="icon-ds block"></i>
        <span class="logo-text">Mind AI</span>
      </router-link>
      <div class="sidebar-actions">
        <a-tooltip title="新对话" placement="right">
          <a-button type="text" size="small" @click="$emit('new-chat')">
            <EditOutlined />
          </a-button>
        </a-tooltip>
        <a-tooltip title="收起侧边栏" placement="right">
          <a-button type="text" size="small" @click="$emit('update:collapsed', !collapsed)">
            <MenuFoldOutlined v-if="!collapsed" />
            <MenuUnfoldOutlined v-else />
          </a-button>
        </a-tooltip>
      </div>
    </div>

    <div class="sidebar-search">
      <a-input v-model:value="searchText" placeholder="搜索对话..." size="small" allow-clear>
        <template #prefix><SearchOutlined /></template>
      </a-input>
    </div>

    <div class="sidebar-list">
      <template v-for="conv in filteredList" :key="conv.id">
        <div class="conv-item" :class="{ active: conv.id === activeConvId }" @click="$emit('select', conv.id)">
          <div class="conv-title">{{ conv.title || '新对话' }}</div>
          <div class="conv-meta">
            <span class="conv-time">{{ conv.time }}</span>
            <div class="conv-item-actions">
              <a-button
                type="text"
                size="small"
                class="conv-pin"
                :class="{ pinned: conv.pinned }"
                @click.stop="$emit('togglePin', conv.id)"
              >
                <PushpinFilled v-if="conv.pinned" />
                <PushpinOutlined v-else />
              </a-button>
              <a-dropdown :trigger="['click']" placement="bottomRight">
                <a-button type="text" size="small" class="conv-more-btn" @click.stop><MoreOutlined /></a-button>
                <template #overlay>
                  <a-menu @click="({ key }) => onMenuAction(key as string, conv.id)">
                    <a-menu-item key="export-json"><ExportOutlined /> 导出 JSON</a-menu-item>
                    <a-menu-item key="export-md"><ExportOutlined /> 导出 Markdown</a-menu-item>
                    <a-menu-divider />
                    <a-menu-item key="delete"
                      ><span class="menu-delete"><DeleteOutlined /> 删除</span></a-menu-item
                    >
                  </a-menu>
                </template>
              </a-dropdown>
            </div>
          </div>
        </div>
      </template>
      <template v-if="filteredList.length === 0 && searchText">
        <div class="conv-empty">未找到匹配的对话</div>
      </template>
      <template v-else-if="filteredList.length === 0">
        <div class="conv-empty">暂无历史对话</div>
      </template>
      <template v-if="hasMore">
        <div class="conv-more" @click="$emit('loadMore')">加载更多</div>
      </template>
    </div>

    <div class="sidebar-footer">
      <a-button
        type="text"
        danger
        size="small"
        block
        :disabled="conversations.length === 0 && messagesCount === 0"
        @click="$emit('clear')"
      >
        <DeleteOutlined /> 清空对话
      </a-button>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import {
  EditOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  DeleteOutlined,
  SearchOutlined,
  PushpinOutlined,
  PushpinFilled,
  MoreOutlined,
  ExportOutlined,
} from '@ant-design/icons-vue'
import type { ChatMessage } from '@/composables/useAgentChat'

export interface Conversation {
  id: string
  title: string
  time: string
  messages?: ChatMessage[]
  pinned?: boolean
}

const props = defineProps<{
  conversations: Conversation[]
  activeConvId: string
  collapsed: boolean
  messagesCount: number
  hasMore?: boolean
}>()

const emit = defineEmits<{
  'update:collapsed': [val: boolean]
  'new-chat': []
  select: [id: string]
  delete: [id: string]
  clear: []
  togglePin: [id: string]
  loadMore: []
  export: [convId: string, format: string]
}>()

const searchText = ref('')

const filteredList = computed(() => {
  if (!searchText.value.trim()) return props.conversations
  const kw = searchText.value.trim().toLowerCase()
  return props.conversations.filter(c => (c.title || '').toLowerCase().includes(kw))
})

function onMenuAction(key: string, convId: string) {
  if (key === 'delete') emit('delete', convId)
  else if (key === 'export-json') emit('export', convId, 'json')
  else if (key === 'export-md') emit('export', convId, 'md')
}
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;

.icon-ds {
  display: block;
  background: linear-gradient(135deg, #818cf8, #c084fc);
  clip-path: polygon(50% 0%, 62% 38%, 100% 50%, 62% 62%, 50% 100%, 38% 62%, 0% 50%, 38% 38%);
  animation: sparkle-pulse 2.4s ease-in-out infinite;
  width: 28px;
  height: 28px;
}

@keyframes sparkle-pulse {
  0%,
  100% {
    opacity: 0.7;
    transform: scale(0.95);
  }
  50% {
    opacity: 1;
    transform: scale(1.05);
  }
}

.chat-sidebar {
  width: $sidebar-width;
  min-width: $sidebar-width;
  background: #f1f5f9;
  border-right: 1px solid $border;
  display: flex;
  flex-direction: column;
  transition:
    width 0.25s ease,
    min-width 0.25s ease;
  overflow: hidden;

  &.collapsed {
    width: 0;
    min-width: 0;
    border-right: none;
  }

  .sidebar-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 12px 14px;
    border-bottom: 1px solid $border;
    .sidebar-logo {
      display: flex;
      align-items: center;
      gap: 8px;
      text-decoration: none;
      color: $text;
      font-weight: 700;
      font-size: 15px;
    }
    .sidebar-actions {
      display: flex;
      gap: 2px;
    }
  }

  .sidebar-search {
    padding: 10px 12px;
    border-bottom: 1px solid $border;
    :deep(.ant-input-affix-wrapper) {
      border-radius: 10px;
      background: #e2e8f0;
      border: 1px solid transparent;
      padding: 4px 10px;
      transition: all 0.2s ease;
      .ant-input {
        background: transparent;
        font-size: 13px;
        height: 28px;
        line-height: 28px;
        &::placeholder {
          color: $text-muted;
          font-size: 12px;
        }
      }
      .anticon {
        color: $text-muted;
      }
      &:hover {
        background: #dde4ed;
      }
      &:focus-within {
        background: #fff;
        border-color: $primary;
        box-shadow: 0 0 0 2px rgba($primary, 0.1);
      }
    }
  }

  .sidebar-list {
    flex: 1;
    overflow-y: auto;
    padding: 8px;

    .conv-item {
      padding: 10px 12px;
      border-radius: 8px;
      cursor: pointer;
      margin-bottom: 2px;
      transition: background 0.15s;
      &:hover {
        background: rgba($primary, 0.06);
      }
      &.active {
        background: rgba($primary, 0.1);
      }
      .conv-title {
        font-size: 13px;
        font-weight: 500;
        color: $text;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }
      .conv-meta {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-top: 2px;
        .conv-time {
          font-size: 11px;
          color: $text-muted;
        }
        .conv-item-actions {
          display: flex;
          align-items: center;
          gap: 0;
          opacity: 0;
          transition: opacity 0.15s;
        }
        .conv-pin {
          font-size: 11px;
          color: $text-muted;
          padding: 0;
          min-width: 22px;
          height: 22px;
          &:hover {
            color: $primary;
          }
          &.pinned {
            opacity: 1;
            color: $primary;
          }
        }
        .conv-more-btn {
          font-size: 14px;
          color: $text-muted;
          padding: 0;
          min-width: 24px;
          height: 24px;
          &:hover {
            color: $text;
          }
        }
      }
      &:hover .conv-item-actions {
        opacity: 1;
      }
    }

    .conv-empty {
      text-align: center;
      color: $text-muted;
      font-size: 13px;
      padding: 24px 0;
    }
    .conv-more {
      text-align: center;
      color: $primary;
      font-size: 12px;
      padding: 10px;
      cursor: pointer;
      border-radius: 6px;
      &:hover {
        background: rgba($primary, 0.06);
      }
    }
  }

  .sidebar-footer {
    padding: 8px;
    border-top: 1px solid $border;
  }
}

.sidebar-list::-webkit-scrollbar {
  width: 4px;
}
.sidebar-list::-webkit-scrollbar-thumb {
  background: #e2e8f0;
  border-radius: 2px;
}
</style>

<style lang="scss">
.menu-delete {
  color: #dc2626;
}
</style>
