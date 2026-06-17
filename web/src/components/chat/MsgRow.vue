<!-- Message row — user / agent / tool / error -->
<template>
  <!-- User message -->
  <template v-if="message.role === 'user'">
    <div class="msg-row user" :class="{ selectable: selectable }">
      <template v-if="selectable">
        <a-checkbox class="msg-check" :checked="selected" @change="$emit('toggleSelect', message.id)" />
      </template>
      <div class="msg-avatar user">U</div>
      <MsgContextMenu
        @copy="emit('copy', message.text || '')"
        @quote="emit('quoteMsg', message.id)"
        @delete="emit('delete', message.id)"
      >
        <div class="msg-content" @contextmenu="onContextMenu">
          <template v-if="message.images && message.images.length > 0">
            <div class="msg-images-row">
              <template v-for="(img, ii) in message.images" :key="ii">
                <a-image :src="img" :width="96" :height="96" class="msg-image-thumb" />
              </template>
            </div>
          </template>
          <template v-if="message.files && message.files.length > 0">
            <div class="msg-files-row">
              <div v-for="(f, i) in message.files" :key="'f-' + i" class="msg-file-chip">
                <FileTextOutlined class="file-icon" />
                <span class="file-name">{{ f.name }}</span>
              </div>
            </div>
          </template>
          <template v-if="message.quote">
            <div class="msg-quote-block">
              <div class="quote-line"></div>
              <div class="quote-body">
                <span class="quote-role">{{ message.quote.role === "user" ? "你" : "AI" }}</span>
                {{ message.quote.text }}
              </div>
            </div>
          </template>
          <div class="msg-bubble user">{{ message.text }}</div>
          <div class="msg-actions">
            <span class="msg-copy" title="复制" @click="$emit('copy', message.text || '')"><CopyOutlined /></span>
            <span class="msg-quote-btn" title="引用" @click="$emit('quote', { text: message.text || '', msgId: message.id, role: 'user' })">
              <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M9 17L4 12l5-5" /><path d="M4 12h10a6 6 0 010 12" />
              </svg>
            </span>
            <template v-if="!selectable">
              <span class="msg-select-trigger" title="选择" @click="$emit('startSelect', message.id)"><CheckSquareOutlined /></span>
            </template>
          </div>
        </div>
      </MsgContextMenu>
    </div>
  </template>

  <!-- AI reply -->
  <template v-else-if="message.role === 'agent'">
    <div class="msg-row assistant" :class="{ selectable: selectable }">
      <template v-if="selectable">
        <a-checkbox class="msg-check" :checked="selected" @change="$emit('toggleSelect', message.id)" />
      </template>
      <div class="msg-avatar ai">
        <i class="icon-ds block ds-small"></i>
      </div>
      <MsgContextMenu
        @copy="emit('copy', message.text || '')"
        @quote="emit('quoteMsg', message.id)"
        @delete="emit('delete', message.id)"
      >
        <div class="msg-content" @contextmenu="onContextMenu">
          <template v-if="message.thinking">
            <details class="thinking-details" :open="!message.text">
              <summary class="thinking-summary">
                <span class="thinking-label">思考过程</span>
                <span class="thinking-chevron">▾</span>
              </summary>
              <div class="thinking-body">{{ message.thinking }}</div>
            </details>
          </template>
          <div class="msg-bubble assistant">
            <template v-for="(seg, si) in messageSegments" :key="si">
              <template v-if="seg.type === 'text' && seg.content.trim()">
                <div class="md-body" v-html="renderSegMd(seg.content)" />
              </template>
              <template v-else-if="seg.type === 'mindmap'">
                <MindMapCard :markdown="seg.content" />
              </template>
              <template v-else-if="seg.type === 'map'">
                <MapCard
                  :title="seg.data.title"
                  :center="seg.data.center"
                  :zoom="seg.data.zoom"
                  :markers="seg.data.markers"
                />
              </template>
              <template v-else-if="seg.type === 'route'">
                <RouteCard
                  :mode="seg.data.mode"
                  :from="seg.data.from"
                  :to="seg.data.to"
                />
              </template>
            </template>
          </div>
          <MsgReferenceCard :references="message.references" />
          <div class="msg-actions">
            <span class="msg-copy" title="复制" @click="$emit('copy', message.text || '')"><CopyOutlined /></span>
            <span class="msg-quote-btn" title="引用" style="transform: scaleX(-1)" @click="$emit('quote', { text: message.text || '', msgId: message.id, role: 'agent' })">
              <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M9 17L4 12l5-5" /><path d="M4 12h10a6 6 0 010 12" />
              </svg>
            </span>
            <span class="msg-feedback" :class="fbClass">
              <span class="fb-btn" title="有帮助" @click="onFeedBack('liked')"><LikeOutlined /></span>
              <span class="fb-btn" title="无帮助" @click="onFeedBack('disliked')"><DislikeOutlined /></span>
            </span>
            <template v-if="ttsSupported">
              <span class="msg-speak" :class="{ active: ttsSpeaking }" :title="ttsSpeaking ? '停止朗读' : '朗读'" @click="onToggleSpeak">
                <template v-if="!ttsSpeaking"><SoundOutlined /></template>
                <template v-else><PauseCircleFilled /></template>
              </span>
            </template>
            <template v-if="!selectable">
              <span class="msg-select-trigger" title="选择" @click="$emit('startSelect', message.id)"><CheckSquareOutlined /></span>
            </template>
          </div>
        </div>
      </MsgContextMenu>
    </div>
  </template>

  <!-- Tool call -->
  <template v-else-if="message.role === 'tool' && message.tool">
    <div class="msg-row tool-row" :class="{ selectable: selectable }">
      <template v-if="selectable">
        <a-checkbox class="msg-check" :checked="selected" @change="$emit('toggleSelect', message.id)" />
      </template>
      <div class="msg-avatar tool-av">🔧</div>
      <div class="msg-content">
        <div class="tool-card" :class="{ expanded: toolExpanded }">
          <div class="tool-header" @click="onToggleTool">
            <span class="tool-name">{{ message.tool.name }}</span>
            <template v-if="message.tool.success === undefined">
              <span class="tool-badge pending">执行中</span>
            </template>
            <template v-else-if="message.tool.success">
              <span class="tool-badge ok">已完成</span>
            </template>
            <template v-else>
              <span class="tool-badge fail">失败</span>
            </template>
            <template v-if="message.tool.result !== undefined">
              <span class="tool-expand-icon">{{ toolExpanded ? "▾" : "▸" }}</span>
            </template>
          </div>
          <template v-if="toolExpanded && message.tool.result !== undefined">
            <div class="tool-detail">
              <pre class="tool-result" :class="{ fail: !message.tool.success }">{{ formattedToolResult }}</pre>
            </div>
          </template>
          <template v-if="toolCanvasData">
            <CanvasPreview :nodes="toolCanvasData.nodes" :edges="toolCanvasData.edges" />
          </template>
        </div>
      </div>
    </div>
  </template>

  <!-- Error -->
  <template v-else-if="message.role === 'error'">
    <div class="msg-row assistant" :class="{ selectable: selectable }">
      <template v-if="selectable">
        <a-checkbox class="msg-check" :checked="selected" @change="$emit('toggleSelect', message.id)" />
      </template>
      <div class="msg-avatar ai">!</div>
      <div class="msg-content">
        <div class="msg-bubble error">{{ message.text }}</div>
        <span class="msg-retry" title="重试" @click="$emit('retry')"><ReloadOutlined /> 重试</span>
      </div>
    </div>
  </template>

  <!-- Text selection floating toolbar -->
  <Teleport to="body">
    <transition name="quote-fade">
      <template v-if="quoteVisible">
        <div
          class="selection-toolbar"
          :style="{ left: `${quotePos.x}px`, top: `${quotePos.y}px` }"
        >
          <span class="toolbar-btn" @click.stop="onQuoteSelection">
            <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" style="transform: scaleX(-1)">
              <path d="M9 17L4 12l5-5" /><path d="M4 12h10a6 6 0 010 12" />
            </svg>
            <span>引用</span>
          </span>
          <span class="toolbar-divider"></span>
          <span class="toolbar-btn" @click.stop="onCopySelection">
            <CopyOutlined />
            <span>复制</span>
          </span>
          <template v-if="ttsSupported">
            <span class="toolbar-divider"></span>
            <span class="toolbar-btn" @click.stop="onSpeakSelection">
              <SoundOutlined />
              <span>朗读</span>
            </span>
          </template>
        </div>
      </template>
    </transition>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onBeforeUnmount } from "vue";
import {
  CopyOutlined, CheckSquareOutlined, LikeOutlined,
  DislikeOutlined, ReloadOutlined, FileTextOutlined,
  SoundOutlined, PauseCircleFilled,
} from "@ant-design/icons-vue";
import type { ChatMessage } from "@/composables/useAgentChat";
import { useSpeech } from "@/composables/useSpeech";
import MindMapCard from "./MindMapCard.vue";
import MapCard from "./MapCard.vue";
import RouteCard from "./RouteCard.vue";
import CanvasPreview from "./CanvasPreview.vue";
import MsgContextMenu from "./MsgContextMenu.vue";
import MsgReferenceCard from "./MsgReferenceCard.vue";

const props = defineProps<{
  message: ChatMessage;
  renderMd: (text: string) => string;
  selectable?: boolean;
  selected?: boolean;
}>();

const emit = defineEmits<{
  copy: [text: string];
  toggleSelect: [msgId: string];
  startSelect: [msgId: string];
  feedback: [msgId: string, type: string];
  quote: [data: { text: string; msgId: string; role: string }];
  quoteMsg: [msgId: string];
  retry: [];
  delete: [msgId: string];
}>();

const toolExpanded = ref(false);
const fbState = ref(props.message.feedback || "");

const fbClass = computed(() => ({
  liked: fbState.value === "liked",
  disliked: fbState.value === "disliked",
}));

watch(() => props.message.feedback, (val) => { fbState.value = val || ""; });

function onToggleTool() {
  if (props.message.tool?.result !== undefined) {
    toolExpanded.value = !toolExpanded.value;
  }
}

const formattedToolResult = computed(() => {
  const result = props.message.tool?.result;
  if (result === undefined) return "";
  if (typeof result === "string") return result;
  try { return JSON.stringify(result, null, 2); } catch { return String(result); }
});

const toolCanvasData = computed(() => {
  const result = props.message.tool?.result;
  if (!result || typeof result !== "object") return null;
  const r = result as Record<string, unknown>;
  const data = (r.data || r) as Record<string, unknown>;
  const diagram = data?.diagram as Record<string, unknown> | undefined;
  if (diagram?.nodes && Array.isArray(diagram.nodes)) {
    return { nodes: diagram.nodes, edges: (diagram.edges as any[]) || [] };
  }
  return null;
});

function onFeedBack(type: string) {
  fbState.value = fbState.value === type ? "" : type;
  emit("feedback", props.message.id, fbState.value);
}

// ── Message segments (mindmap / map / route detection) ──

const BLOCK_RE = /```(mindmap|map|route)\s*\n([\s\S]*?)```/g;

interface MsgSegment {
  type: "text" | "mindmap" | "map" | "route";
  content?: string;
  data?: any;
}

const messageSegments = computed(() => {
  const text = props.message.text || "";
  BLOCK_RE.lastIndex = 0;
  const segments: MsgSegment[] = [];
  let lastIndex = 0;
  let match: RegExpExecArray | null;
  while ((match = BLOCK_RE.exec(text)) !== null) {
    if (match.index > lastIndex) {
      segments.push({ type: "text", content: text.slice(lastIndex, match.index) });
    }
    const blockType = match[1];
    const blockContent = match[2].trim();
    if (blockType === "mindmap") {
      segments.push({ type: "mindmap", content: blockContent });
    } else {
      try {
        const data = JSON.parse(blockContent);
        segments.push({ type: blockType as "map" | "route", data });
      } catch {
        // Invalid JSON — render as code block
        segments.push({ type: "text", content: `\`\`\`${blockType}\n${blockContent}\n\`\`\`` });
      }
    }
    lastIndex = match.index + match[0].length;
  }
  if (lastIndex < text.length) {
    segments.push({ type: "text", content: text.slice(lastIndex) });
  }
  return segments.length > 0 ? segments : [{ type: "text", content: text }];
});

function renderSegMd(text: string): string {
  if (!text.trim()) return "";
  return props.renderMd(text);
}

// ── TTS ──

const { speaking: ttsSpeaking, supported: ttsSupported, speak, stop } = useSpeech();

function onToggleSpeak() {
  if (ttsSpeaking.value) {
    stop();
  } else {
    speak(props.message.text || "");
  }
}

// ── Text selection floating toolbar ──

const quoteVisible = ref(false);
const quotePos = ref({ x: 0, y: 0 });

function onContextMenu(e: MouseEvent) {
  const sel = window.getSelection()?.toString().trim();
  if (!sel) return;
  e.preventDefault();
  e.stopPropagation();
  quotePos.value = { x: e.clientX + 8, y: e.clientY + 4 };
  quoteVisible.value = true;
}

function hideContextMenu() {
  quoteVisible.value = false;
}

function onCopySelection() {
  const text = window.getSelection()?.toString().trim();
  const fallback = props.message.text || "";
  emit("copy", text || fallback);
  quoteVisible.value = false;
}

function onQuoteSelection() {
  const text = window.getSelection()?.toString().trim();
  const fallback = props.message.text || "";
  emit("quote", {
    text: text || fallback,
    msgId: props.message.id,
    role: props.message.role,
  });
  quoteVisible.value = false;
}

function onSpeakSelection() {
  const text = window.getSelection()?.toString().trim();
  if (text) speak(text);
  quoteVisible.value = false;
}

onMounted(() => {
  document.addEventListener("click", hideContextMenu);
});

onBeforeUnmount(() => {
  document.removeEventListener("click", hideContextMenu);
});
</script>

<style lang="scss" scoped>
@use "@/assets/styles/variables.scss" as *;

.icon-ds {
  display: block;
  background: linear-gradient(135deg, #818cf8, #c084fc);
  clip-path: polygon(50% 0%, 62% 38%, 100% 50%, 62% 62%, 50% 100%, 38% 62%, 0% 50%, 38% 38%);
  width: 28px; height: 28px;
  &.ds-small { width: 18px; height: 18px; animation: none; }
}

.msg-row {
  display: flex; gap: 12px; margin-bottom: 20px; align-items: flex-start;

  &.user {
    flex-direction: row-reverse;
    .msg-content { display: flex; flex-direction: column; align-items: flex-end; }
    .msg-bubble, .msg-quote-block { width: fit-content; max-width: 100%; }
  }
  &.selectable { cursor: pointer; }

  .msg-check { margin-top: 6px; flex-shrink: 0; }

  .msg-avatar {
    width: 32px; height: 32px; border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 13px; font-weight: 700; flex-shrink: 0;
    &.user { background: #e0e7ff; color: $primary; }
    &.ai { background: linear-gradient(135deg, $primary, #7c3aed); color: #fff; }
    &.tool-av { background: #fef3c7; color: #d97706; font-size: 14px; }
  }

  .msg-content { max-width: 75%; min-width: 0; }

  .msg-bubble {
    padding: 10px 16px; border-radius: 16px; font-size: 14px; line-height: 1.65;
    &.user { background: $primary; color: #fff; border-bottom-right-radius: 4px; }
    &.assistant { background: #f1f5f9; color: $text; border-bottom-left-radius: 4px; }
    &.error { background: #fef2f2; color: #dc2626; border: 1px solid #fecaca; }
  }

  .msg-actions {
    display: flex; align-items: center; gap: 2px; margin-top: 4px;
  }

  .msg-copy, .msg-quote-btn, .msg-select-trigger {
    display: inline-flex; align-items: center; padding: 3px 6px;
    font-size: 12px; color: $text-muted; cursor: pointer; border-radius: 4px;
    transition: all 0.15s; opacity: 0;
    &:hover { color: $primary; background: #f1f5f9; }
  }

  .msg-speak {
    display: inline-flex; align-items: center; padding: 3px 6px;
    font-size: 12px; color: $text-muted; cursor: pointer; border-radius: 4px;
    transition: all 0.15s; opacity: 0;
    &:hover { color: $primary; background: #f1f5f9; }
    &.active {
      opacity: 1; color: $primary; background: #eef2ff;
    }
  }

  .msg-feedback {
    display: inline-flex; align-items: center; gap: 2px; opacity: 0;
    .fb-btn {
      display: inline-flex; align-items: center; padding: 3px 5px;
      font-size: 12px; color: $text-muted; cursor: pointer; border-radius: 4px;
      transition: all 0.15s;
      &:hover { color: $primary; background: #f1f5f9; }
    }
    &.liked, &.disliked { opacity: 1; }
    &.liked .fb-btn:first-child { color: $primary; }
    &.disliked .fb-btn:last-child { color: #dc2626; }
  }

  .msg-retry {
    display: inline-flex; align-items: center; gap: 4px; margin-top: 6px;
    padding: 2px 10px; font-size: 12px; color: #dc2626; cursor: pointer;
    border-radius: 6px; background: #fef2f2; border: 1px solid #fecaca;
    transition: all 0.15s; opacity: 0;
    &:hover { background: #fee2e2; border-color: #fca5a5; }
  }

  &:hover .msg-copy, &:hover .msg-speak, &:hover .msg-feedback, &:hover .msg-select-trigger,
  &:hover .msg-quote-btn, &:hover .msg-retry { opacity: 1; }
}

.msg-quote-block {
  display: flex; gap: 6px; margin-bottom: 6px; padding: 6px 10px;
  background: rgba(79, 70, 229, 0.04); border-radius: 8px;
  .quote-body { flex: 1; font-size: 12px; color: $text-secondary; line-height: 1.5; }
  .quote-role {
    display: inline-block; padding: 1px 5px; margin-right: 4px;
    font-size: 10px; font-weight: 600; color: $primary;
    background: rgba($primary, 0.1); border-radius: 3px;
  }
  .quote-line { width: 3px; border-radius: 2px; background: $primary; flex-shrink: 0; opacity: 0.5; align-self: stretch; }
}

.msg-images-row {
  display: flex; flex-wrap: wrap; gap: 8px; justify-content: flex-end; margin-bottom: 8px;
  .msg-image-thumb {
    border-radius: 12px; overflow: hidden;
    border: 2px solid rgba($primary, 0.1); cursor: pointer;
    &:hover { transform: scale(1.06); border-color: $primary; }
  }
}

.msg-files-row {
  display: flex; flex-wrap: wrap; gap: 6px; justify-content: flex-end; margin-bottom: 8px;
  .msg-file-chip {
    display: inline-flex; align-items: center; gap: 5px;
    padding: 5px 10px; border-radius: 8px;
    background: rgba(79, 70, 229, 0.06); border: 1px solid rgba(79, 70, 229, 0.15);
    .file-icon { font-size: 14px; color: $primary; flex-shrink: 0; }
    .file-name { font-size: 12px; color: $text; max-width: 180px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  }
}

.thinking-details {
  margin-bottom: 8px; border: 1px solid #e2e8f0; border-radius: 10px;
  background: #fafafa; overflow: hidden;
  &[open] { border-color: #d4d4d8; }
  .thinking-summary {
    display: flex; align-items: center; gap: 6px; padding: 6px 12px;
    cursor: pointer; user-select: none; font-size: 12px; color: #71717a; list-style: none;
    &:hover { background: #f4f4f5; }
    .thinking-chevron { margin-left: auto; font-size: 10px; }
  }
  .thinking-body {
    padding: 8px 12px 10px; font-size: 12px; line-height: 1.6;
    color: #71717a; white-space: pre-wrap; word-break: break-word;
    border-top: 1px solid #e4e4e7; max-height: 200px; overflow-y: auto;
  }
}

.tool-card {
  background: #fffbeb; border: 1px solid #fde68a; border-radius: 10px;
  padding: 8px 12px; font-size: 13px; cursor: pointer;
  .tool-header { display: flex; align-items: center; gap: 8px; }
  .tool-name { font-weight: 600; color: #92400e; font-family: "Fira Code", "Consolas", monospace; font-size: 12px; }
  .tool-badge {
    font-size: 11px; padding: 1px 7px; border-radius: 8px; font-weight: 500;
    &.pending { background: #fef3c7; color: #b45309; }
    &.ok { background: #d1fae5; color: #065f46; }
    &.fail { background: #fee2e2; color: #991b1b; }
  }
  .tool-expand-icon { margin-left: auto; font-size: 10px; color: #a16207; }
  .tool-detail { margin-top: 8px; padding-top: 8px; border-top: 1px solid #fde68a; }
  .tool-result {
    margin: 0; padding: 8px; border-radius: 6px; font-size: 11px; line-height: 1.5;
    white-space: pre-wrap; word-break: break-all; max-height: 180px; overflow-y: auto;
    background: #f0fdf4; color: #166534;
    &.fail { background: #fef2f2; color: #991b1b; }
  }
}

// ── Text selection floating toolbar ──

.selection-toolbar {
  position: fixed;
  z-index: 999;
  display: flex;
  align-items: center;
  padding: 4px 6px;
  background: #fff;
  border-radius: 10px;
  box-shadow: 0 4px 20px rgba(79, 70, 229, 0.12), 0 2px 8px rgba(0, 0, 0, 0.06),
    0 0 0 0.5px rgba(0, 0, 0, 0.06);
  transform: none;
  transition: box-shadow 0.2s, transform 0.15s;
  user-select: none;

  .toolbar-btn {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 4px 10px;
    font-size: 13px;
    font-weight: 500;
    color: #333;
    cursor: pointer;
    border-radius: 6px;
    transition: background 0.12s;
    &:hover {
      background: rgba(79, 70, 229, 0.06);
    }
    &:active {
      transform: scale(0.96);
    }
  }
  .toolbar-divider {
    width: 1px;
    height: 18px;
    background: #e2e8f0;
    margin: 0 2px;
  }
}

.quote-fade-enter-active,
.quote-fade-leave-active {
  transition: opacity 0.12s ease;
}
.quote-fade-enter-from,
.quote-fade-leave-to {
  opacity: 0;
}
</style>
