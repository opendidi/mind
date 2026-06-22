<!--
 * @Descripttion:
 * @version: 1.0.0
 * @Author: htang
 * @Date: 2023-09-11 08:50:37
 * @LastEditors: htang
 * @LastEditTime: 2025-08-21 09:33:00
-->
<template>
  <div class="app-page">
    <Editor />
    <!-- 弹窗 -->
    <CommonModal ref="commonModalRef" :width="'90vw'" />
    <!-- 小窗展示 -->
    <IframeModal ref="iframeModalRef" />
    <div class="fix flex flex-col">
      <a-tooltip placement="left">
        <template #title>
          <span>适合窗口大小</span>
        </template>
        <t-icon name="fullscreen-1" class="mb-2" @click="onFitView(true, 0)" />
      </a-tooltip>
      <a-tooltip placement="left">
        <template #title>
          <span>短边适合窗口大小</span>
        </template>
        <t-icon name="fullscreen-exit-1" @click="onFitView(false, 20)" />
      </a-tooltip>
    </div>
  </div>
</template>

<script lang="ts" setup>
import { onMounted, onBeforeUnmount, ref, nextTick, watch } from "vue";
import Editor from "@/components/Meta2D/Editor/index.vue";
import CommonModal from "@/components/Meta2D/CommonModal/index.vue";
import IframeModal from "@/components/Meta2D/IframeModal/index.vue";
import { useSelection } from "@/services/selections";

const { selections } = useSelection();

const commonModalRef = ref(null);
const iframeModalRef = ref(null);

watch(
  () => selections.pen,
  (data) => {
    if (data) {
      const { events } = data;
      if (events) {
        events.some((_: { action: number; value: string; params?: string }) => {
          switch (_.action) {
            case 7:
              switch (_.value) {
                case "l-dialog":
                  {
                    meta2d.on(_.value, (e: unknown) => {
                      if (commonModalRef.value) {
                        Object.assign(commonModalRef.value, {
                          visible: true,
                          title: "自定义弹窗",
                        });
                        nextTick(() => {
                          commonModalRef.value.init(_);
                        });
                      }
                    });
                  }
                  break;
                case "iframe-dialog":
                  {
                    meta2d.on(_.value, (e: unknown) => {
                      if (iframeModalRef.value) {
                        Object.assign(iframeModalRef.value, {
                          visible: true,
                          title: "展示",
                          url: _.params,
                        });
                        nextTick(() => {
                          iframeModalRef.value.init(e);
                        });
                      }
                    });
                  }
                  break;
              }
              break;
          }
        });
      }
    }
  }
);

const onFitView = (fit: boolean, viewPadding: number) => {
  meta2d.fitView(fit, viewPadding);
};

function loadCanvas() {
  const data = localStorage.getItem("meta2d");
  if (!data) return;
  try {
    const parsed = JSON.parse(data);
    parsed.locked = 1; // read-only in preview mode
    parsed.rule = false;
    meta2d.open(parsed);
    meta2d.fitView(true, 24);
  } catch { /* ignore */ }
}

// Listen for Agent-triggered canvas mutations from parent window (chat page)
function onMutated(e: MessageEvent) {
  if (e.data?.type === "canvas:mutated") {
    loadCanvas();
  }
}
window.addEventListener("message", onMutated);

onMounted(() => {
  loadCanvas();
});

onBeforeUnmount(() => {
  window.removeEventListener("message", onMutated);
});
</script>

<style lang="less" scoped>
.app-page {
  height: 100vh;
  .fix {
    position: fixed;
    right: 20px;
    bottom: 20px;
    background: #fff;
    z-index: 10;
    .t-icon {
      font-size: 26px;
      cursor: pointer;
      &:hover {
        color: #1890ff;
      }
    }
  }
}
</style>