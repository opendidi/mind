<!-- FileCard — renders ```files blocks as image/file preview grid -->
<template>
  <div class="file-card">
    <div class="fc-header">
      <svg class="fc-icon" viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
        <polyline points="14 2 14 8 20 8" />
        <line x1="16" y1="13" x2="8" y2="13" />
        <line x1="16" y1="17" x2="8" y2="17" />
        <polyline points="10 9 9 9 8 9" />
      </svg>
      <span class="fc-label">文件列表</span>
      <span class="fc-count">{{ files.length }}</span>
    </div>
    <div class="fc-grid">
      <div
        v-for="(f, idx) in files"
        :key="idx"
        class="fc-item"
        @click="onClick(f)"
      >
        <!-- Image preview -->
        <div class="fc-thumb" v-if="isImage(f)">
          <img
            :src="f.url || f.thumb_path"
            :alt="f.name"
            @error="onImgError"
            loading="lazy"
          />
        </div>
        <!-- File icon for non-images -->
        <div class="fc-thumb fc-file-icon" v-else>
          <svg viewBox="0 0 24 24" width="32" height="32" fill="none" stroke="currentColor" stroke-width="1.5">
            <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
            <polyline points="14 2 14 8 20 8" />
          </svg>
        </div>
        <!-- File info -->
        <div class="fc-name" :title="f.name">{{ f.name }}</div>
        <div class="fc-meta">
          <span v-if="f.extension" class="fc-ext">{{ f.extension }}</span>
          <span v-if="f.size" class="fc-size">{{ formatSize(f.size) }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  files: Array<{
    name: string;
    url?: string;
    thumb_path?: string;
    type?: string;
    extension?: string;
    size?: number;
  }>;
}>();

const IMG_EXTS = new Set(['jpg', 'jpeg', 'png', 'gif', 'webp', 'svg', 'bmp', 'ico']);

function isImage(f: any): boolean {
  const ext = (f.extension || '').toLowerCase();
  const type = (f.type || '').toLowerCase();
  return IMG_EXTS.has(ext) || type === 'image' || type === 'panorama';
}

function formatSize(bytes: number): string {
  if (!bytes) return '';
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / 1048576).toFixed(1) + ' MB';
}

function onClick(f: any) {
  if (f.url) window.open(f.url, '_blank', 'noopener');
}

function onImgError(e: Event) {
  const el = e.target as HTMLElement;
  el.style.display = 'none';
}
</script>

<style lang="scss" scoped>
.file-card {
  margin: 8px 0;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  background: #fff;
  overflow: hidden;
}

.fc-header {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  background: #fafafa;
  border-bottom: 1px solid #f0f0f0;
}

.fc-icon {
  color: #8b8b8b;
  flex-shrink: 0;
}

.fc-label {
  font-size: 12px;
  font-weight: 500;
  color: #666;
}

.fc-count {
  font-size: 11px;
  color: #999;
  background: #f0f0f0;
  padding: 0 6px;
  border-radius: 8px;
}

.fc-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding: 10px 12px;
}

.fc-item {
  width: 120px;
  cursor: pointer;
  border-radius: 8px;
  overflow: hidden;
  transition: transform 0.15s, box-shadow 0.15s;

  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  }
}

.fc-thumb {
  width: 120px;
  height: 90px;
  border-radius: 6px;
  overflow: hidden;
  background: #f5f5f5;
  display: flex;
  align-items: center;
  justify-content: center;

  img {
    width: 100%;
    height: 100%;
    object-fit: cover;
  }

  &.fc-file-icon {
    color: #d1d5db;
  }
}

.fc-name {
  font-size: 11px;
  color: #333;
  margin-top: 4px;
  padding: 0 2px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.fc-meta {
  display: flex;
  gap: 4px;
  padding: 0 2px;
  font-size: 10px;
  color: #aaa;
}

.fc-ext {
  text-transform: uppercase;
  background: #f0f0f0;
  padding: 0 4px;
  border-radius: 3px;
}
</style>
