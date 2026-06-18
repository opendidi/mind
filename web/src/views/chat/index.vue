<!-- Mind AI Chat — full page chat view -->
<template>
  <div class="ds-chat-page">
    <!-- Sidebar -->
    <ChatSidebar
      :conversations="conversations"
      :activeConvId="activeConvId"
      :collapsed="sidebarCollapsed"
      :messagesCount="messages.length"
      :hasMore="hasMoreConversations"
      @update:collapsed="sidebarCollapsed = $event"
      @new-chat="onNewChat"
      @select="onSwitchConv"
      @delete="onDeleteConv"
      @clear="onClearData"
      @togglePin="onTogglePin"
      @loadMore="onLoadMoreConversations"
      @export="onExportConv"
    />

    <!-- Main chat area -->
    <main class="chat-main">
      <!-- Header -->
      <header class="chat-header">
        <div class="header-left">
          <a-button type="text" class="header-icon-btn" @click="sidebarCollapsed = !sidebarCollapsed">
            <template v-if="sidebarCollapsed">
              <MenuUnfoldOutlined />
            </template>
            <template v-else>
              <MenuFoldOutlined />
            </template>
          </a-button>
          <span class="header-divider" />
          <span class="header-title">
            {{ activeConvTitle || "AI 对话" }}
          </span>
        </div>
        <div class="header-right">
          <span v-if="loading || switchingConv" class="header-status working">
            <span class="status-dot" /> 处理中
          </span>
          <span v-else-if="messages.length > 0" class="header-status idle">
            <span class="status-dot" /> 就绪
          </span>
          <a-tooltip title="新建对话">
            <a-button class="header-icon-btn" size="small" type="text" @click="onNewChat">
              <PlusOutlined />
            </a-button>
          </a-tooltip>
          <a-tooltip title="文件管理">
            <a-button class="header-icon-btn" size="small" type="text" @click="openFileManager">
              <FolderOpenOutlined />
            </a-button>
          </a-tooltip>
          <span class="user-avatar">{{ userName.charAt(0) || "U" }}</span>
        </div>
      </header>

      <!-- Messages area -->
      <div ref="msgListRef" class="msg-area" @scroll="onMsgAreaScroll">
        <!-- Empty state -->
        <template v-if="messages.length === 0 && !loading && !switchingConv">
          <WelcomePanel @suggest="onSuggestion" />
        </template>

        <!-- Plan card -->
        <PlanCard :plan="currentPlan" />

        <!-- Messages -->
        <div class="msg-inner">
          <template
            v-for="item in groupedMessages"
            :key="Array.isArray(item) ? 'tg-' + item[0].id : item.id"
          >
            <!-- Tool group (2+ consecutive tool calls) -->
            <template v-if="Array.isArray(item) && item.length > 1">
              <details class="tool-group-details">
                <summary class="tool-group-summary">
                  <span class="tool-group-label">
                    🔧 工具调用 ({{ item.length }})
                  </span>
                  <span class="tool-group-chevron">▾</span>
                </summary>
                <div class="tool-group-body">
                  <MsgRow
                    v-for="m in item"
                    :key="m.id"
                    :message="m"
                    :renderMd="renderMd"
                    :selectable="selectMode"
                    :selected="selectedIds.has(m.id)"
                    @copy="copyText"
                    @toggleSelect="onToggleSelect"
                    @startSelect="onStartSelect"
                    @feedback="onMsgFeedback"
                    @quote="onQuoteMsg"
                    @quoteMsg="onQuoteMsgId"
                    @delete="onDeleteMsg"
                    @retry="onRetry"
                  />
                </div>
              </details>
            </template>
            <!-- Single message (or single tool) -->
            <MsgRow
              v-else
              :message="Array.isArray(item) ? item[0] : item"
              :renderMd="renderMd"
              :selectable="selectMode"
              :selected="
                selectedIds.has(Array.isArray(item) ? item[0].id : item.id)
              "
              @copy="copyText"
              @toggleSelect="onToggleSelect"
              @startSelect="onStartSelect"
              @feedback="onMsgFeedback"
              @quote="onQuoteMsg"
              @quoteMsg="onQuoteMsgId"
              @delete="onDeleteMsg"
              @retry="onRetry"
            />
          </template>

          <!-- Loading animation -->
          <template v-if="loading || switchingConv">
            <div class="msg-row assistant">
              <div class="msg-avatar ai thinking">
                <i class="icon-ds block ds-small"></i>
              </div>
              <div class="msg-content">
                <div class="thinking-bubble">
                  <span class="think-text">{{ loadingStatus }}</span>
                  <span class="think-dots">
                    <span class="dot"></span>
                    <span class="dot"></span>
                    <span class="dot"></span>
                  </span>
                </div>
              </div>
            </div>
          </template>
        </div>
        <div ref="msgEndRef" />
      </div>

      <!-- Scroll-to-bottom FAB -->
      <transition name="fab-fade">
        <template v-if="!isNearBottom">
          <div class="scroll-fab" @click="scrollToBottom(true)">
            <span class="fab-icon">↓</span>
          </div>
        </template>
      </transition>

      <!-- Selection toolbar -->
      <template v-if="messages.length > 0 && selectMode">
        <div class="select-toolbar">
          <span class="select-count">
            {{
              selectedIds.size > 0 ? `已选 ${selectedIds.size} 条` : "选择消息"
            }}
          </span>
          <a-button
            size="small"
            type="text"
            class="select-all-btn"
            @click="onSelectAll"
          >
            <CheckSquareOutlined />
          </a-button>
          <div class="select-spacer" />
          <a-button
            size="small"
            type="text"
            class="select-cancel-btn"
            @click="onCancelSelect"
          >
            <CloseOutlined />
          </a-button>
          <a-button
            size="small"
            class="select-del-btn"
            @click="onBatchDelete"
            :disabled="selectedIds.size === 0"
          >
            <DeleteOutlined />
          </a-button>
        </div>
      </template>

      <!-- Input area -->
      <ChatInput
        :loading="loading || switchingConv"
        :modelList="modelList"
        :modelIdx="activeModelIdx"
        :quotedText="quotedText"
        @update:modelIdx="activeModelIdx = $event"
        @send="onSend"
        @abort="onAbort"
        @removeQuote="quotedText = null"
      />
    </main>

    <!-- Canvas preview panel (shown when agent modified canvas) -->
    <aside v-if="showCanvasPreview" class="canvas-preview-panel">
      <div class="preview-header">
        <span class="preview-title">画布预览</span>
        <div class="preview-actions">
          <a-button size="small" type="link" @click="openCanvasEditor">
            打开编辑器
          </a-button>
          <a-button size="small" type="text" @click="showCanvasPreview = false">
            ✕
          </a-button>
        </div>
      </div>
      <iframe
        ref="previewIframe"
        class="preview-iframe"
        :src="previewUrl"
        @load="onPreviewLoaded"
      />
    </aside>

    <!-- Canvas preview toggle (when hidden but changes exist) -->
    <transition name="fab-fade">
      <div
        v-if="!showCanvasPreview && hasCanvasChanges"
        class="canvas-preview-fab"
        @click="showCanvasPreview = true"
        title="查看画布修改"
      >
        <span class="fab-badge" />
        <span class="fab-label">画布</span>
      </div>
    </transition>

    <FileManager ref="fileManagerRef" mode="view" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onBeforeUnmount } from "vue";
import { message } from "ant-design-vue";
import {
  MenuUnfoldOutlined,
  MenuFoldOutlined,
  DeleteOutlined,
  CheckSquareOutlined,
  CloseOutlined,
  FolderOpenOutlined,
  PlusOutlined,
} from "@ant-design/icons-vue";
import { useRouter, useRoute } from "vue-router";
import MarkdownIt from "markdown-it";
import { useUserStore } from "@/store/modules/user";
import {
  useAgentChat,
  type QuoteInfo,
  type ChatFile,
  type ChatMessage,
} from "@/composables/useAgentChat";
import { useConversations } from "@/composables/useConversations";
import { useMessageSelect } from "@/composables/useMessageSelect";
import { useScrollToBottom } from "@/composables/useScrollToBottom";
import { executeCanvasTool } from "@/utils/canvasBridge";
import ChatSidebar from "@/components/chat/ChatSidebar.vue";
import ChatInput from "@/components/chat/ChatInput.vue";
import PlanCard from "@/components/chat/PlanCard.vue";
import MsgRow from "@/components/chat/MsgRow.vue";
import WelcomePanel from "@/components/chat/WelcomePanel.vue";
import FileManager from "@/components/FileManager/index.vue";

const md = new MarkdownIt({
  html: false,
  linkify: true,
  typographer: true,
  breaks: true,
});
const renderMd = (text: string) => md.render(text);

const router = useRouter();
const route = useRoute();
const userName = computed(() => "用户");

// UI state
const sidebarCollapsed = ref(false);
const quotedText = ref<QuoteInfo | null>(null);
const fileManagerRef = ref<InstanceType<typeof FileManager>>();

function openFileManager() {
  fileManagerRef.value!.visible = true;
  fileManagerRef.value!.init();
  fileManagerRef.value!.initMaterialFolder();
}

// Canvas preview
const CANVAS_TOOLS = ['add_pen', 'canvas_add_pen', 'add_line', 'canvas_add_line',
  'update_pen', 'canvas_update_pen', 'delete_pen', 'canvas_delete_pen',
  'clear', 'canvas_clear', 'add_diagram', 'canvas_add_diagram',
  'layout_auto_arrange', 'layout_align'];
const hasCanvasChanges = ref(false);
const showCanvasPreview = ref(false);
const previewIframe = ref<HTMLIFrameElement>();
const previewUrl = `${window.location.origin}${window.location.pathname}#/preview`;

function onPreviewLoaded() {
  // iframe loaded — canvas is displayed
}

function openCanvasEditor() {
  window.open(`${window.location.origin}${window.location.pathname}#/`, '_blank');
}

// Plan state — driven by composable's built-in plan tracker
const currentPlan = computed(() => {
  const p = plan.value;
  if (!p) return null;
  return {
    goal: p.goal,
    risk: p.risk,
    steps: p.nodes.map((n) => ({
      id: n.id,
      desc: n.desc,
      tool: null as string | null,
      confirm: n.confirm ?? false,
      status: n.status,
    })),
  };
});

// Loading status labels
const TOOL_LABELS: Record<string, string> = {
  create_pen: "创建图形",
  delete_pen: "删除图形",
  update_pen: "更新图形",
  move_pen: "移动图形",
  layout: "自动排版",
  create_mindmap: "生成思维导图",
  search_blueprints: "搜索蓝图",
  load_blueprint: "加载蓝图",
  web_search: "搜索网络信息",
};

const loadingStatus = computed(() => {
  if (!loading.value) return "";
  if (thinkingText.value) return thinkingText.value;
  if (currentTool.value) {
    const label = TOOL_LABELS[currentTool.value] || currentTool.value;
    return `正在${label}`;
  }
  if (currentPlan.value) return "分析任务中";
  return "AI 思考中";
});

// Group consecutive tool messages into collapsible blocks
const groupedMessages = computed(() => {
  const result: Array<ChatMessage | ChatMessage[]> = [];
  let toolGroup: ChatMessage[] = [];
  for (const msg of messages.value) {
    if (msg.role === "tool") {
      toolGroup.push(msg);
    } else {
      if (toolGroup.length > 0) {
        result.push([...toolGroup]);
        toolGroup = [];
      }
      result.push(msg);
    }
  }
  if (toolGroup.length > 0) result.push([...toolGroup]);
  return result;
});

// Models
const modelList = ref<{ id: string }[]>([]);
const activeModelIdx = ref(0);

watch(activeModelIdx, (val) => {
  if (modelList.value[val]) localStorage.setItem("chat-model-idx", String(val));
});

// Agent composable — plan / tool calls / SSE events handled centrally
const {
  messages,
  loading,
  currentTool,
  thinkingText,
  plan,
  send: agentSend,
  abort: agentAbort,
  retry: agentRetry,
  clear: agentClear,
} = useAgentChat({
  userId: useUserStore().userInfo?.id || undefined,
  onToolResult(tool, args, success, result) {
    executeCanvasTool(tool, args as Record<string, unknown>, success, result);
    if (success && CANVAS_TOOLS.includes(tool)) {
      hasCanvasChanges.value = true;
      showCanvasPreview.value = true;
    }
  },
  onDone() {
    saveCurrentConv();
  },
});

// Scroll management
const { msgListRef, msgEndRef, isNearBottom, scrollToBottom, onMsgAreaScroll } =
  useScrollToBottom(messages, loading);

// Conversation management
const {
  conversations,
  activeConvId,
  hasMoreConversations,
  switchingConv,
  activeConvTitle,
  saveCurrentConv,
  onNewChat,
  onSwitchConv,
  onDeleteConv,
  onTogglePin,
  onLoadMoreConversations,
  onExportConv,
  onClearData,
  loadConversationList,
} = useConversations({
  messages,
  currentPlan,
  agentAbort,
  agentClear,
  router,
  route,
  onLoaded: () => scrollToBottom(true),
});

// Multi-select
const {
  selectMode,
  selectedIds,
  onToggleSelect,
  onStartSelect,
  onSelectAll,
  onCancelSelect,
  onBatchDelete,
} = useMessageSelect(messages, () => saveCurrentConv());

// Message actions
async function copyText(text: string) {
  try {
    await navigator.clipboard.writeText(text);
    message.success("已复制");
  } catch {
    message.error("复制失败");
  }
}

function onQuoteMsg(data: { text: string; msgId: string; role: string }) {
  quotedText.value = {
    text: data.text,
    msgId: data.msgId,
    role: data.role as QuoteInfo["role"],
  };
}

function onQuoteMsgId(msgId: string) {
  const msg = messages.value.find((m) => m.id === msgId);
  if (!msg) return;
  const text = msg.text || "";
  const role: QuoteInfo["role"] =
    msg.role === "user" || msg.role === "agent" ? msg.role : "agent";
  quotedText.value = { text, msgId, role };
}

function onDeleteMsg(msgId: string) {
  messages.value = messages.value.filter((m) => m.id !== msgId);
  saveCurrentConv();
}

function onMsgFeedback(_msgId: string, _type: string) {
  // Feedback persistence placeholder
  saveCurrentConv();
}

function onSuggestion(text: string) {
  onSend(text, [], [], []);
}

// Send
async function onSend(
  text: string,
  imageUrls: string[],
  docMarkers: string[],
  docFiles: ChatFile[],
  quotedTextParam?: QuoteInfo
) {
  const hasImages = imageUrls.length > 0;
  const hasDocs = docMarkers.length > 0;
  const hasAnyAttach = hasImages || hasDocs;
  if ((!text && !hasAnyAttach) || loading.value) return;

  // Build API text with internal markers (for agent tool reference)
  const parts: string[] = [];
  if (hasDocs) parts.push(docMarkers.join("\n"));
  if (hasImages)
    parts.push(imageUrls.map((u, i) => `[图片${i + 1}: ${u}]`).join("\n"));
  if (text) parts.push(text);
  const apiText = parts.join("\n");

  isNearBottom.value = true;
  await agentSend(
    apiText,
    hasImages ? imageUrls : undefined,
    undefined,
    quotedTextParam,
    hasDocs ? docFiles : undefined
  );
}

function onAbort() {
  agentAbort();
}
function onRetry() {
  agentRetry();
}

// Lifecycle
onMounted(() => {
  loadConversationList();
  const saved = localStorage.getItem("chat-model-idx");
  if (saved) activeModelIdx.value = Number(saved);
});

onBeforeUnmount(() => {
  agentAbort();
});
</script>

<style lang="scss" scoped>
@use "@/assets/styles/variables.scss" as *;

.icon-ds {
  display: block;
  background: linear-gradient(135deg, #818cf8, #c084fc);
  clip-path: polygon(
    50% 0%,
    62% 38%,
    100% 50%,
    62% 62%,
    50% 100%,
    38% 62%,
    0% 50%,
    38% 38%
  );
  animation: sparkle-pulse 2.4s ease-in-out infinite;
  width: 28px;
  height: 28px;
  &.ds-big {
    width: 56px;
    height: 56px;
  }
  &.ds-small {
    width: 18px;
    height: 18px;
    animation: none;
  }
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

.ds-chat-page {
  display: flex;
  height: 100vh;
  width: 100vw;
  background: $bg;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
    "Helvetica Neue", Arial, "PingFang SC", "Microsoft YaHei", sans-serif;
  overflow: hidden;
}

.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  height: 100vh;
  background: $surface;
}

.chat-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 16px;
  border-bottom: 1px solid $border;
  background: $surface;
  flex-shrink: 0;
  height: 48px;
  gap: 12px;

  .header-left {
    display: flex;
    align-items: center;
    gap: 8px;
    min-width: 0;
    flex: 1;
  }
  .header-title {
    font-size: 14px;
    font-weight: 600;
    color: $text;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .header-divider {
    width: 1px;
    height: 20px;
    background: #e2e8f0;
    flex-shrink: 0;
  }
  .header-right {
    display: flex;
    align-items: center;
    gap: 4px;
    flex-shrink: 0;
  }
  .header-icon-btn {
    width: 32px;
    height: 32px;
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #6b7280;
    border: none;
    background: transparent;
    cursor: pointer;
    font-size: 15px;
    transition: all 0.15s;
    &:hover {
      background: #f1f5f9;
      color: #374151;
    }
  }
  .header-status {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 12px;
    font-weight: 500;
    padding: 2px 10px;
    border-radius: 12px;
    margin-right: 6px;
    &.working {
      color: #b45309;
      background: #fef3c7;
    }
    &.idle {
      color: #64748b;
      background: #f1f5f9;
    }
    .status-dot {
      width: 6px;
      height: 6px;
      border-radius: 50%;
      background: #94a3b8;
    }
    &.working .status-dot {
      background: #f59e0b;
      animation: status-blink 1.2s ease-in-out infinite;
    }
  }
  .user-avatar {
    width: 28px;
    height: 28px;
    border-radius: 50%;
    background: $primary-gradient;
    color: #fff;
    font-size: 12px;
    font-weight: 600;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    margin-left: 4px;
  }
}

@keyframes status-blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}

.msg-area {
  flex: 1;
  overflow-y: auto;
  scrollbar-gutter: stable;
  padding: 20px 0;
  position: relative;
  .msg-inner {
    max-width: $msg-max-width;
    margin: 0 auto;
    padding: 0 24px;
  }
}

.msg-row {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
  .msg-avatar {
    width: 32px;
    height: 32px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 13px;
    font-weight: 700;
    flex-shrink: 0;
    &.ai {
      background: linear-gradient(135deg, $primary, #7c3aed);
      color: #fff;
      :deep(.ds-small) {
        filter: brightness(0) invert(1);
      }
    }
  }
  .msg-content {
    max-width: 75%;
    min-width: 0;
  }
}

.select-toolbar {
  display: flex;
  align-items: center;
  gap: 6px;
  max-width: $msg-max-width;
  margin: 0 auto;
  padding: 0 24px 10px;
  .select-count {
    font-size: 13px;
    color: $text-secondary;
    font-weight: 500;
    min-width: 60px;
  }
  .select-spacer {
    flex: 1;
  }
  .select-all-btn,
  .select-cancel-btn {
    width: 32px;
    height: 32px;
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 0;
    color: $text-muted;
    transition: all 0.15s;
    &:hover {
      color: $text-secondary;
      background: #f1f5f9;
    }
  }
  .select-del-btn {
    width: 32px;
    height: 32px;
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 0;
    color: $text-muted;
    background: transparent;
    border: none;
    transition: all 0.15s;
    &:hover:not(:disabled) {
      color: #dc2626;
      background: #fef2f2;
    }
    &:disabled {
      color: #d1d5db;
      cursor: not-allowed;
    }
  }
}

.msg-avatar.ai.thinking {
  animation: avatar-glow 2s ease-in-out infinite;
}

@keyframes avatar-glow {
  0%,
  100% {
    box-shadow: 0 0 0 0 rgba(129, 140, 248, 0.4);
  }
  50% {
    box-shadow: 0 0 0 8px rgba(129, 140, 248, 0);
  }
}

.thinking-bubble {
  background: #f8fafc;
  padding: 12px 18px;
  border-radius: 16px;
  border-bottom-left-radius: 4px;
  border: 1px solid #e2e8f0;
  display: inline-flex;
  align-items: center;
  gap: 10px;
  .think-text {
    font-size: 13px;
    color: #64748b;
    font-weight: 500;
  }
  .think-dots {
    display: inline-flex;
    align-items: center;
    gap: 4px;
  }
  .dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: #94a3b8;
    animation: dot-pulse 1.4s infinite both;
    &:nth-child(2) {
      animation-delay: 0.2s;
    }
    &:nth-child(3) {
      animation-delay: 0.4s;
    }
  }
}

@keyframes dot-pulse {
  0%,
  80%,
  100% {
    transform: scale(0.5);
    opacity: 0.3;
  }
  40% {
    transform: scale(1);
    opacity: 1;
  }
}

.scroll-fab {
  position: absolute;
  bottom: 24px;
  right: 24px;
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: $surface;
  border: 1px solid $border;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
  transition: transform 0.15s, box-shadow 0.15s;
  z-index: 10;
  &:hover {
    transform: scale(1.1);
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12);
  }
  .fab-icon {
    font-size: 16px;
    color: $text-secondary;
    line-height: 1;
  }
}

.fab-fade-enter-active,
.fab-fade-leave-active {
  transition: opacity 0.2s, transform 0.2s;
}
.fab-fade-enter-from,
.fab-fade-leave-to {
  opacity: 0;
  transform: translateY(8px);
}

.msg-area::-webkit-scrollbar {
  width: 5px;
}
.msg-area::-webkit-scrollbar-track {
  background: transparent;
}
.msg-area::-webkit-scrollbar-thumb {
  background: transparent;
  border-radius: 3px;
  transition: background 0.3s;
}
.msg-area:hover::-webkit-scrollbar-thumb {
  background: #d1d5db;
}
.msg-area::-webkit-scrollbar-thumb:hover {
  background: #9ca3af;
}

// Collapsible tool group (consecutive tool calls)
.tool-group-details {
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  background: #fafafa;
  overflow: hidden;
  margin-bottom: 16px;

  &[open] {
    border-color: #d4d4d8;
  }

  .tool-group-summary {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 6px 12px;
    cursor: pointer;
    user-select: none;
    font-size: 12px;
    color: #71717a;
    list-style: none;

    &:hover {
      background: #f4f4f5;
    }

    .tool-group-chevron {
      margin-left: auto;
      font-size: 10px;
    }
  }

  .tool-group-body {
    padding: 12px;
    border-top: 1px solid #e4e4e7;

    :deep(.msg-row) {
      margin-bottom: 8px;
    }
    :deep(.msg-row:last-child) {
      margin-bottom: 4px;
    }
  }
}

// Canvas preview panel (chat page)
.canvas-preview-panel {
  width: 320px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  border-left: 1px solid $border;
  background: #fafafa;
  .preview-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 8px 12px;
    border-bottom: 1px solid $border;
    .preview-title {
      font-size: 13px;
      font-weight: 600;
      color: $text;
    }
    .preview-actions {
      display: flex;
      gap: 4px;
      align-items: center;
    }
  }
  .preview-iframe {
    flex: 1;
    border: none;
    width: 100%;
  }
}

.canvas-preview-fab {
  position: fixed;
  bottom: 100px;
  right: 24px;
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  background: $surface;
  border: 1px solid $border;
  border-radius: 20px;
  cursor: pointer;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
  z-index: 20;
  transition: transform 0.15s, box-shadow 0.15s;
  &:hover {
    transform: scale(1.05);
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12);
  }
  .fab-badge {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #f59e0b;
    animation: badge-pulse 2s infinite;
  }
  .fab-label {
    font-size: 12px;
    font-weight: 500;
    color: $text-secondary;
  }
}

@keyframes badge-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}
</style>

<style lang="scss">
@use "@/assets/styles/md-body.scss" as *;
</style>
