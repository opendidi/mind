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
          <template v-if="searchType === 'image'">
            搜索了 <strong>{{ references.length }}</strong> 张图片
          </template>
          <template v-else>
            搜索了 <strong>{{ references.length }}</strong> 个网页
          </template>
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

    <!-- Image gallery (when searchType is "image") -->
    <div v-if="searchType === 'image' && expanded" class="refs-gallery">
      <template v-for="ref in references" :key="ref.url">
        <div
          class="gallery-item"
          :title="ref.title || ref.snippet || ''"
          @click="previewRef = ref"
        >
          <div class="gallery-thumb">
            <img
              v-if="ref.image"
              :src="ref.image"
              :alt="ref.title"
              loading="lazy"
              referrerpolicy="no-referrer"
            />
            <div v-else class="gallery-placeholder">
              <svg viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="1.5">
                <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
                <circle cx="8.5" cy="8.5" r="1.5" />
                <path d="M21 15l-5-5L5 21" />
              </svg>
            </div>
          </div>
          <span class="gallery-title">{{ ref.title || ref.domain || '图片' }}</span>
          <span v-if="ref.domain" class="gallery-domain">{{ ref.domain }}</span>
        </div>
      </template>
    </div>

    <!-- Image lightbox -->
    <Teleport to="body">
      <transition name="lightbox-fade">
        <div v-if="previewRef" class="gallery-lightbox-overlay" @click="previewRef = null">
          <img :src="previewRef.image" :alt="previewRef.title" class="gallery-lightbox-img" @click.stop />
          <div class="gallery-lightbox-info" @click.stop>
            <span class="gallery-lightbox-title">{{ previewRef.title || '图片' }}</span>
            <template v-if="previewRef.domain">
              <span class="gallery-lightbox-domain">{{ previewRef.domain }}</span>
            </template>
            <a
              class="gallery-lightbox-source"
              :href="previewRef.url"
              target="_blank"
              rel="noopener noreferrer"
            >
              <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
                <polyline points="15 3 21 3 21 9" />
                <line x1="10" y1="14" x2="21" y2="3" />
              </svg>
              查看来源
            </a>
          </div>
          <span class="gallery-lightbox-close" @click="previewRef = null">&times;</span>
        </div>
      </transition>
    </Teleport>

    <!-- Reference list (web/news only) -->
    <div v-show="expanded && searchType !== 'image'" class="refs-list">
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
  references?: Array<{ title?: string; url: string; snippet?: string; domain?: string; image?: string }>
  searchType?: string  // "web" | "news" | "image"
}>()

const emit = defineEmits<{
  selectRefs: [refs: Array<{ title?: string; url: string; snippet?: string; domain?: string }>]
}>()

const expanded = ref(false)
const openIdx = ref(-1)
const previewRef = ref<{ title?: string; url: string; image?: string; domain?: string } | null>(null)
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

// ── Image gallery ──────────────────────────────────────

.refs-gallery {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 6px;
  padding: 6px 10px 10px 10px;
  border-top: 1px solid #f0f0f0;
}

.gallery-item {
  display: flex;
  flex-direction: column;
  gap: 3px;
  border-radius: 8px;
  overflow: hidden;
  cursor: pointer;
  transition: background 0.12s, transform 0.12s;

  &:hover {
    background: #f5f5f5;
    transform: translateY(-1px);
  }
}

.gallery-thumb {
  width: 100%;
  aspect-ratio: 1;
  overflow: hidden;
  border-radius: 6px;
  background: #f3f4f6;
  border: 1px solid #e5e7eb;

  img {
    width: 100%;
    height: 100%;
    object-fit: cover;
    display: block;
  }
}

.gallery-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #d1d5db;
  background: #f9fafb;
}

.gallery-title {
  font-size: 10px;
  color: #374151;
  line-height: 1.3;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  padding: 0 2px;
}

.gallery-domain {
  font-size: 10px;
  color: #9ca3af;
  padding: 0 2px 2px 2px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

// ── Gallery lightbox ────────────────────────────────────

.gallery-lightbox-overlay {
  position: fixed;
  inset: 0;
  z-index: 2000;
  background: rgba(0, 0, 0, 0.78);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}

.gallery-lightbox-img {
  max-width: 85vw;
  max-height: 78vh;
  border-radius: 6px;
  box-shadow: 0 8px 40px rgba(0, 0, 0, 0.35);
  cursor: default;
  object-fit: contain;
}

.gallery-lightbox-info {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 12px;
  padding: 6px 16px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  cursor: default;
}

.gallery-lightbox-title {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.85);
  max-width: 360px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.gallery-lightbox-domain {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.45);
  background: rgba(255, 255, 255, 0.1);
  border-radius: 4px;
  padding: 1px 6px;
}

.gallery-lightbox-source {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.75);
  text-decoration: none;
  padding: 3px 10px;
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.08);
  transition: background 0.15s, color 0.15s;

  &:hover {
    background: rgba(255, 255, 255, 0.18);
    color: #fff;
  }
}

.gallery-lightbox-close {
  position: absolute;
  top: 16px;
  right: 20px;
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.12);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  cursor: pointer;
  transition: background 0.15s;

  &:hover {
    background: rgba(255, 255, 255, 0.22);
  }
}

.lightbox-fade-enter-active,
.lightbox-fade-leave-active {
  transition: opacity 0.2s ease;
}
.lightbox-fade-enter-from,
.lightbox-fade-leave-to {
  opacity: 0;
}
</style>
