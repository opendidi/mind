<!-- MindMap card — renders ```mindmap blocks via markmap -->
<template>
  <div class="mindmap-card" :class="{ fullscreen: isFullscreen }" ref="containerRef">
    <div class="mm-header">
      <span class="mm-title">思维导图</span>
      <span class="mm-actions">
        <span class="mm-btn" title="适应视图" @click="onFit">
          <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="3" />
            <path d="M12 3v3m0 12v3M3 12h3m12 0h3" />
          </svg>
        </span>
        <span class="mm-btn" title="放大" @click="onZoomIn">+</span>
        <span class="mm-btn" title="缩小" @click="onZoomOut">−</span>
        <span class="mm-btn" :title="isFullscreen ? '退出全屏' : '全屏'" @click="onToggleFullscreen">
          <template v-if="!isFullscreen">
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M8 3H5a2 2 0 00-2 2v3m18 0V5a2 2 0 00-2-2h-3m0 18h3a2 2 0 002-2v-3M3 16v3a2 2 0 002 2h3" />
            </svg>
          </template>
          <template v-else>
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M8 3v3a2 2 0 01-2 2H3m18 0h-3a2 2 0 01-2-2V3m0 18v-3a2 2 0 012-2h3M3 16h3a2 2 0 012 2v3" />
            </svg>
          </template>
        </span>
      </span>
    </div>
    <template v-if="renderError">
      <pre class="mm-fallback">{{ markdown }}</pre>
    </template>
    <svg v-else ref="svgRef" class="mm-svg"></svg>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import { Transformer } from 'markmap-lib'
import { Markmap } from 'markmap-view'

const props = defineProps<{
  markdown: string
}>()

const containerRef = ref<HTMLElement>()
const svgRef = ref<SVGElement>()
const isFullscreen = ref(false)
const renderError = ref(false)

let mmInstance: Markmap | null = null
let transformer: Transformer | null = null

// Depth-based color palette — matches markmap repl style
const DEPTH_COLORS = [
  '#f97316', // orange   - depth 0 (root)
  '#eab308', // yellow   - depth 1
  '#22c55e', // green    - depth 2
  '#06b6d4', // cyan     - depth 3
  '#3b82f6', // blue     - depth 4
  '#8b5cf6', // purple   - depth 5
  '#ec4899', // pink     - depth 6+
]

// Walk the node tree and apply depth-based colors
function colorNodes(node: any, depth: number) {
  node.state = node.state || {}
  node.state.color = DEPTH_COLORS[Math.min(depth, DEPTH_COLORS.length - 1)]
  if (node.children) {
    for (const child of node.children) {
      colorNodes(child, depth + 1)
    }
  }
}

function build() {
  if (!svgRef.value) return
  const md = props.markdown || ''
  if (!md.trim()) return

  if (!transformer) {
    transformer = new Transformer()
  }

  try {
    const { root } = transformer.transform(md)
    if (!root || !root.children || root.children.length === 0) {
      renderError.value = true
      return
    }

    // Apply depth-based colors (markmap repl style)
    colorNodes(root, 0)

    if (mmInstance) {
      mmInstance.destroy()
      mmInstance = null
    }

    renderError.value = false
    mmInstance = Markmap.create(
      svgRef.value!,
      {
        autoFit: true,
        duration: 300,
        initialExpandLevel: 3,
        maxWidth: 240,
        nodeMinHeight: 16,
        paddingX: 12,
        spacingHorizontal: 70,
        spacingVertical: 10,
        zoom: true,
        pan: true,
        toggleRecursively: true,
      },
      root,
    )
  } catch (e) {
    console.warn('MindMap render error:', e)
    renderError.value = true
  }
}

function onFit() {
  mmInstance?.fit()
}

function onZoomIn() {
  mmInstance?.rescale(1.3)
}

function onZoomOut() {
  mmInstance?.rescale(0.75)
}

function onToggleFullscreen() {
  isFullscreen.value = !isFullscreen.value
}

function onEsc(e: KeyboardEvent) {
  if (e.key === 'Escape' && isFullscreen.value) {
    isFullscreen.value = false
  }
}

onMounted(() => {
  nextTick(build)
  document.addEventListener('keydown', onEsc)
})

onBeforeUnmount(() => {
  document.removeEventListener('keydown', onEsc)
  mmInstance?.destroy()
  mmInstance = null
})

watch(
  () => props.markdown,
  () => {
    nextTick(build)
  },
)
</script>

<style lang="scss" scoped>
.mindmap-card {
  margin: 12px 0;
  border: 1px solid #d1d5db;
  border-radius: 12px;
  overflow: hidden;
  background: #fff;
  height: 480px;
  display: flex;
  flex-direction: column;
  transition: all 0.3s ease;

  &.fullscreen {
    position: fixed;
    inset: 0;
    z-index: 1100;
    height: 100vh;
    border-radius: 0;
    border: none;
    margin: 0;
  }
}

.mm-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 14px;
  background: #f8fafc;
  border-bottom: 1px solid #e5e7eb;
  flex-shrink: 0;
}

.mm-title {
  font-size: 13px;
  font-weight: 600;
  color: #374151;
}

.mm-actions {
  display: flex;
  align-items: center;
  gap: 4px;
}

.mm-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 600;
  color: #6b7280;
  transition: all 0.15s;
  &:hover {
    background: #e5e7eb;
    color: #374151;
  }
}

.mm-svg {
  flex: 1;
  width: 100%;
  min-height: 0;
  display: block;
  cursor: grab;
  &:active {
    cursor: grabbing;
  }
}

.mm-fallback {
  flex: 1;
  margin: 12px;
  padding: 12px;
  background: #fefce8;
  border: 1px solid #facc15;
  border-radius: 8px;
  font-size: 12px;
  line-height: 1.6;
  color: #92400e;
  white-space: pre-wrap;
  overflow-y: auto;
}
</style>
