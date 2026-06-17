<template>
  <div class="canvas-preview-card">
    <div class="cp-header">
      <span class="cp-title">🎨 画布预览</span>
      <span v-if="nodeCount" class="cp-badge">{{ nodeCount }} 节点 · {{ edgeCount }} 连线</span>
    </div>
    <div :ref="setContainerRef" class="cp-body"></div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, nextTick } from "vue";
import { Meta2d, register, registerAnchors } from "@meta2d/core";
import { flowPens, flowAnchors } from "@meta2d/flow-diagram";

interface DiagramNode {
  id?: string; pen_id?: string; type?: string; text?: string;
  x?: number; y?: number; width?: number; height?: number;
  background?: string; color?: string; fontSize?: number;
  borderWidth?: number; borderColor?: string;
}

interface DiagramEdge {
  from?: string; to?: string; _from_id?: string; _to_id?: string;
  text?: string; line_type?: string; arrow?: string;
}

const props = defineProps<{
  nodes?: DiagramNode[];
  edges?: DiagramEdge[];
}>();

const nodeCount = computed(() => props.nodes?.length || 0);
const edgeCount = computed(() => props.edges?.length || 0);

let containerEl: HTMLElement | null = null;
let meta2d: any = null;
let inited = false;
let observer: IntersectionObserver | null = null;

function setContainerRef(el: any) {
  containerEl = (el as HTMLElement) || null;
}

const TYPE_MAP: Record<string, string> = {
  rectangle: "rectangle", circle: "circle", triangle: "triangle",
  diamond: "diamond", pentagon: "pentagon", star: "star", text: "text",
};

const COLOR_DEFAULTS: Record<string, { background: string; color: string }> = {
  rectangle: { background: "#e8f4fd", color: "#1e40af" },
  circle: { background: "#fef3c7", color: "#92400e" },
  triangle: { background: "#fce4ec", color: "#c62828" },
  diamond: { background: "#f3e5f5", color: "#6a1b9a" },
  pentagon: { background: "#e8f5e9", color: "#2e7d32" },
  star: { background: "#fff8e1", color: "#f57f17" },
  text: { background: "transparent", color: "#333" },
};

function initCanvas() {
  if (!containerEl || inited) return;
  inited = true;

  // Register pen types
  register(flowPens());
  registerAnchors(flowAnchors());

  meta2d = new Meta2d(containerEl as any, {
    background: "transparent",
    rule: false,
    locked: 1,
  });

  nextTick(() => renderContent());
}

function renderContent() {
  if (!meta2d || !props.nodes?.length) return;

  const logicalToActual = new Map<string, string>();
  const stores: any[] = [];

  for (const node of props.nodes) {
    const penType = (node.type || "rectangle").toLowerCase();
    const name = TYPE_MAP[penType] || "rectangle";
    const defaults = COLOR_DEFAULTS[name] || COLOR_DEFAULTS.rectangle;
    const pen: any = {
      name,
      text: node.text || "",
      x: node.x ?? 0,
      y: node.y ?? 0,
      width: node.width || 120,
      height: node.height || 60,
      background: node.background || defaults.background,
      color: node.color || defaults.color,
      fontSize: node.fontSize || 14,
      lineWidth: node.borderWidth || 1,
      borderColor: node.borderColor || "#d1d5db",
    };
    if (name === "circle") {
      pen.width = pen.height = Math.min(pen.width, pen.height) || 80;
    }

    const actualPen = meta2d.addPen(pen);
    if (actualPen) {
      stores.push(actualPen);
      const logicalId = node.pen_id || node.id || "";
      const actualId = actualPen.id || actualPen.penId || "";
      if (logicalId) logicalToActual.set(logicalId, actualId);
    }
  }

  for (const edge of props.edges || []) {
    const fromLogical = edge._from_id || edge.from || "";
    const toLogical = edge._to_id || edge.to || "";
    const fromId = logicalToActual.get(fromLogical) || fromLogical;
    const toId = logicalToActual.get(toLogical) || toLogical;

    if (!fromId || !toId) continue;

    const fromPen = meta2d.findOne(fromId);
    const toPen = meta2d.findOne(toId);
    if (!fromPen || !toPen) continue;

    const fromAnchor = fromPen.anchors?.[0];
    const toAnchor = toPen.anchors?.[0];
    const line: any = {
      anchors: [fromAnchor, toAnchor],
      from: fromAnchor,
      to: toAnchor,
      lineWidth: 2,
      color: edge.color || "#94a3b8",
      text: edge.text || "",
      fontSize: 12,
      animate: false,
    };
    const arrow = edge.arrow || "end";
    if (arrow === "end" || arrow === "both") line.toArrow = "triangleSolid";
    if (arrow === "start" || arrow === "both") line.fromArrow = "triangleSolid";

    meta2d.addLine(line);
  }

  // Render and fit view
  meta2d.render();
  setTimeout(() => {
    try { meta2d.fitView(40); } catch { /* ignore */ }
  }, 80);
}

onMounted(() => {
  if (!containerEl) return;

  if (typeof IntersectionObserver !== "undefined") {
    observer = new IntersectionObserver(
      (entries) => {
        if (entries[0]?.isIntersecting && !inited) {
          nextTick(initCanvas);
          observer?.disconnect();
          observer = null;
        }
      },
      { rootMargin: "200px" }
    );
    observer.observe(containerEl);
  } else {
    nextTick(initCanvas);
  }
});

onBeforeUnmount(() => {
  observer?.disconnect();
  if (meta2d) {
    try { meta2d.destroy?.(); } catch { /* ignore */ }
    meta2d = null;
  }
});
</script>

<style lang="scss" scoped>
.canvas-preview-card {
  margin: 10px 0;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  overflow: hidden;
  background: #fff;
  min-width: 420px;
  width: 100%;
}

.cp-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  background: #f8fafc;
  border-bottom: 1px solid #e2e8f0;

  .cp-title {
    font-size: 12px;
    font-weight: 600;
    color: #475569;
  }

  .cp-badge {
    font-size: 11px;
    color: #94a3b8;
    background: #f1f5f9;
    padding: 1px 8px;
    border-radius: 8px;
  }
}

.cp-body {
  width: 100%;
  height: clamp(300px, 50vh, 480px);
}
</style>
