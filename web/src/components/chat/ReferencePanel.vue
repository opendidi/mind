<!-- ReferencePanel — DeepSeek-style right drawer showing web search references -->
<template>
  <Teleport to="body">
    <Transition name="ref-drawer-slide">
      <div v-if="visible" class="ref-drawer-overlay" @click.self="close">
        <div class="ref-drawer">
          <!-- Header -->
          <div class="ref-drawer-header">
            <div class="ref-drawer-title">
              <svg
                class="ref-icon-globe"
                viewBox="0 0 24 24"
                width="18"
                height="18"
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
              <span>参考来源</span>
              <span class="ref-count">{{ references.length }}</span>
            </div>
            <button class="ref-close-btn" @click="close">
              <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M18 6L6 18M6 6l12 12" />
              </svg>
            </button>
          </div>

          <!-- Reference list -->
          <div class="ref-drawer-body">
            <div v-for="(ref, idx) in references" :key="idx" class="ref-item" @click="openUrl(ref.url)">
              <div class="ref-item-index">{{ idx + 1 }}</div>
              <div class="ref-item-content">
                <div class="ref-item-header">
                  <img
                    v-if="ref.url"
                    class="ref-favicon"
                    :src="faviconUrl(ref.url)"
                    @error="onFaviconError"
                    width="16"
                    height="16"
                  />
                  <span class="ref-domain">{{ ref.domain || extractDomain(ref.url) }}</span>
                </div>
                <div class="ref-item-title">{{ ref.title || ref.url }}</div>
                <div v-if="ref.snippet" class="ref-item-snippet">{{ ref.snippet }}</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
defineProps<{
  visible: boolean
  references: Array<{ title?: string; url: string; snippet?: string; domain?: string }>
}>()

const emit = defineEmits<{ close: [] }>()

function close() {
  emit('close')
}

function openUrl(url: string) {
  if (url) window.open(url, '_blank', 'noopener')
}

function extractDomain(url: string): string {
  try {
    const u = new URL(url)
    return u.hostname.replace(/^www\./, '')
  } catch {
    console.warn('[ReferencePanel] extractDomain: invalid URL —', url)
    return ''
  }
}

function faviconUrl(url: string): string {
  try {
    const u = new URL(url)
    return `https://www.google.com/s2/favicons?domain=${u.hostname}&sz=32`
  } catch {
    console.warn('[ReferencePanel] faviconUrl: invalid URL —', url)
    return ''
  }
}

function onFaviconError(e: Event) {
  const img = e.target as HTMLImageElement
  img.style.display = 'none'
}
</script>

<style lang="scss" scoped>
.ref-drawer-overlay {
  position: fixed;
  inset: 0;
  z-index: 1500;
  background: rgba(0, 0, 0, 0.3);
  display: flex;
  justify-content: flex-end;
}

.ref-drawer {
  width: 400px;
  max-width: 90vw;
  height: 100%;
  background: #fff;
  box-shadow: -4px 0 24px rgba(0, 0, 0, 0.1);
  display: flex;
  flex-direction: column;
}

.ref-drawer-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 18px;
  border-bottom: 1px solid #f0f0f0;
  flex-shrink: 0;
}

.ref-drawer-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 15px;
  font-weight: 600;
  color: #1a1a1a;

  .ref-icon-globe {
    color: #4f46e5;
  }

  .ref-count {
    font-size: 12px;
    font-weight: 500;
    color: #6b7280;
    background: #f3f4f6;
    padding: 1px 8px;
    border-radius: 10px;
  }
}

.ref-close-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  border-radius: 8px;
  border: none;
  background: transparent;
  color: #6b7280;
  cursor: pointer;
  transition: all 0.15s;

  &:hover {
    background: #f3f4f6;
    color: #1a1a1a;
  }
}

.ref-drawer-body {
  flex: 1;
  overflow-y: auto;
  padding: 8px 0;
}

.ref-item {
  display: flex;
  gap: 12px;
  padding: 12px 18px;
  cursor: pointer;
  transition: background 0.12s;

  &:hover {
    background: #f9fafb;
  }

  & + .ref-item {
    border-top: 1px solid #f5f5f5;
  }
}

.ref-item-index {
  width: 22px;
  height: 22px;
  border-radius: 6px;
  background: #f3f4f6;
  color: #6b7280;
  font-size: 11px;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  margin-top: 2px;
}

.ref-item-content {
  flex: 1;
  min-width: 0;
}

.ref-item-header {
  display: flex;
  align-items: center;
  gap: 5px;
  margin-bottom: 4px;
}

.ref-favicon {
  width: 16px;
  height: 16px;
  border-radius: 2px;
  flex-shrink: 0;
}

.ref-domain {
  font-size: 11px;
  color: #9ca3af;
  text-transform: lowercase;
}

.ref-item-title {
  font-size: 13.5px;
  font-weight: 500;
  color: #1a1a1a;
  line-height: 1.4;
  margin-bottom: 4px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;

  .ref-item:hover & {
    color: #4f46e5;
  }
}

.ref-item-snippet {
  font-size: 12px;
  color: #9ca3af;
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

// Drawer slide-in animation
.ref-drawer-slide-enter-active,
.ref-drawer-slide-leave-active {
  transition: opacity 0.25s ease;

  .ref-drawer {
    transition: transform 0.25s ease;
  }
}

.ref-drawer-slide-enter-from,
.ref-drawer-slide-leave-to {
  opacity: 0;

  .ref-drawer {
    transform: translateX(100%);
  }
}
</style>
