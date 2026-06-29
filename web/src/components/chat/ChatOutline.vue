<!-- Chat outline — floating popover/drawer for heading navigation -->
<template>
  <teleport to="body">
    <transition name="outline-fade">
      <div v-if="visible" class="outline-overlay">
        <!-- Backdrop -->
        <div class="outline-backdrop" @click="$emit('close')" />

        <!-- Panel -->
        <aside class="outline-drawer" :class="{ 'mobile-open': mobileOpen }">
        <!-- Header -->
        <div class="outline-header">
          <span class="outline-title">大纲</span>
          <div class="outline-header-actions">
            <a-tooltip title="刷新" placement="bottom">
              <a-button size="small" type="text" class="header-btn" @click="refresh">
                <ReloadOutlined />
              </a-button>
            </a-tooltip>
            <a-tooltip title="关闭" placement="bottom">
              <a-button size="small" type="text" class="header-btn" @click="$emit('close')">
                <CloseOutlined />
              </a-button>
            </a-tooltip>
          </div>
        </div>

        <!-- Search -->
        <OutlineSearch v-model="outline.searchQuery.value" @esc="onSearchEsc" />

        <!-- Tree -->
        <div
          ref="treeContainerRef"
          class="outline-tree-container"
          tabindex="0"
          @keydown="onTreeKeydown"
        >
          <OutlineTree
            :filtered-groups="outline.filteredGroups.value"
            :collapsed-groups="outline.collapsedGroups.value"
            :active-id="activeHeading.activeId.value"
            :search-query="outline.searchQuery.value"
            @toggle-group="outline.toggleGroup"
            @select="onSelectHeading"
          />
        </div>
      </aside>
      </div>
    </transition>
  </teleport>
</template>

<script setup lang="ts">
import { ref, watch, nextTick, onMounted, toRef } from 'vue'
import { ReloadOutlined, CloseOutlined } from '@ant-design/icons-vue'
import type { ChatMessage } from '@/composables/useAgentChat'
import { useOutline, type Heading } from '@/composables/useOutline'
import { useActiveHeading } from '@/composables/useActiveHeading'
import OutlineSearch from './OutlineSearch.vue'
import OutlineTree from './OutlineTree.vue'

const props = defineProps<{
  visible: boolean
  messages: ChatMessage[]
  loading: boolean
  msgListRef: HTMLElement | null | undefined
}>()

defineEmits<{
  close: []
}>()

const messagesRef = toRef(props, 'messages')
const loadingRef = toRef(props, 'loading')

const outline = useOutline(messagesRef, loadingRef)

const treeContainerRef = ref<HTMLElement>()
const msgListRefWrapper = toRef(props, 'msgListRef')

const activeHeading = useActiveHeading(msgListRefWrapper)

// Refresh observer when outline becomes visible and groups change
watch(
  () => props.visible,
  (v) => {
    if (v) {
      nextTick(() => {
        outline.forceRefresh()
        activeHeading.refresh()
      })
    }
  },
)

watch(() => outline.groups.value, () => {
  if (props.visible) {
    nextTick(() => activeHeading.refresh())
  }
})

function onSelectHeading(heading: Heading) {
  outline.scrollToHeading(heading)
}

function onSearchEsc() {
  outline.searchQuery.value = ''
}

// ── Keyboard navigation ─────────────────────────────────────

const focusedIdx = ref(-1)

function getVisibleHeadings(): Heading[] {
  const result: Heading[] = []
  for (const group of outline.filteredGroups.value) {
    if (outline.collapsedGroups.value.has(group.msgId)) continue
    const walk = (list: Heading[]) => {
      for (const h of list) {
        result.push(h)
        if (h.children.length > 0) walk(h.children)
      }
    }
    walk(group.headings)
  }
  return result
}

function onTreeKeydown(e: KeyboardEvent) {
  const headings = getVisibleHeadings()
  if (headings.length === 0) return

  switch (e.key) {
    case 'ArrowDown':
      e.preventDefault()
      focusedIdx.value = Math.min(focusedIdx.value + 1, headings.length - 1)
      break
    case 'ArrowUp':
      e.preventDefault()
      focusedIdx.value = Math.max(focusedIdx.value - 1, 0)
      break
    case 'Enter':
      e.preventDefault()
      if (focusedIdx.value >= 0 && focusedIdx.value < headings.length) {
        onSelectHeading(headings[focusedIdx.value])
      }
      break
    case 'Escape':
      e.preventDefault()
      outline.searchQuery.value = ''
      focusedIdx.value = -1
      break
  }

  if (focusedIdx.value >= 0) {
    nextTick(() => {
      const items = treeContainerRef.value?.querySelectorAll('.outline-item')
      items?.[focusedIdx.value]?.scrollIntoView({ block: 'nearest' })
    })
  }
}

// ── Mobile drawer (forced open for mobile) ────────────────

const mobileOpen = ref(false)

function openMobile() {
  mobileOpen.value = true
}

function closeMobile() {
  mobileOpen.value = false
}

defineExpose({ openMobile, closeMobile })

// ── Lifecycle ───────────────────────────────────────────────

function refresh() {
  outline.forceRefresh()
  nextTick(() => activeHeading.refresh())
}

// Handle Esc key globally to close
function onGlobalKeydown(e: KeyboardEvent) {
  if (e.key === 'Escape' && props.visible) {
    // Don't close if search is focused
    const active = document.activeElement
    if (active?.closest('.outline-search')) return
    // Don't close if tree container is focused (keyboard nav)
    if (active === treeContainerRef.value) return
    // emit close
    // Handled by backdrop click — but Esc should also close
  }
}

onMounted(() => {
  document.addEventListener('keydown', onGlobalKeydown)
})

// Cleanup not strictly needed due to teleport, but good practice
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;

// ── Overlay wrapper (single child for <Transition>) ─────

.outline-overlay {
  position: fixed;
  inset: 0;
  z-index: 90;
  pointer-events: none;

  > * {
    pointer-events: auto;
  }
}

// ── Backdrop ────────────────────────────────────────────────

.outline-backdrop {
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0.2);
}

// ── Drawer panel ────────────────────────────────────────────

.outline-drawer {
  position: absolute;
  top: 0;
  right: 0;
  bottom: 0;
  width: 300px;
  display: flex;
  flex-direction: column;
  background: var(--color-surface, #fff);
  border-left: 1px solid var(--color-border, $border);
  box-shadow: -4px 0 24px rgba(0, 0, 0, 0.1);
  overflow: hidden;
}

// ── Header ──────────────────────────────────────────────────

.outline-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 8px 0 14px;
  height: 44px;
  border-bottom: 1px solid var(--color-border, $border);
  flex-shrink: 0;

  .outline-title {
    font-size: 14px;
    font-weight: 600;
    color: var(--color-text, $text);
  }

  .outline-header-actions {
    display: flex;
    align-items: center;
    gap: 2px;
  }

  .header-btn {
    width: 28px;
    height: 28px;
    border-radius: 6px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #6b7280;
    border: none;
    background: transparent;
    cursor: pointer;
    font-size: 13px;
    transition: all 0.15s;

    &:hover {
      background: #f1f5f9;
      color: #374151;
    }
  }
}

// ── Tree container ─────────────────────────────────────────

.outline-tree-container {
  flex: 1;
  overflow: hidden;
  outline: none;
}

// ── Transitions ─────────────────────────────────────────────

.outline-fade-enter-active,
.outline-fade-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}

.outline-fade-enter-from,
.outline-fade-leave-to {
  .outline-backdrop {
    opacity: 0;
  }
  .outline-drawer {
    transform: translateX(100%);
  }
}

.outline-fade-enter-active {
  .outline-drawer {
    transition: transform 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  }
}

.outline-fade-leave-active {
  .outline-drawer {
    transition: transform 0.2s ease-in;
  }
}

// ── Mobile: full-width ─────────────────────────────────────

@media (max-width: 768px) {
  .outline-drawer {
    width: 100vw;
  }
}
</style>
