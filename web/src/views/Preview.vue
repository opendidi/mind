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
    <CommonModal ref="commonModal" :width="'90vw'" />
    <!-- 小窗展示 -->
    <IframeModal ref="iframeModal" />
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
import { onMounted, getCurrentInstance, nextTick, watch } from "vue";
import Editor from "@/components/Meta2D/Editor/index.vue";
import CommonModal from "@/components/Meta2D/CommonModal/index.vue";
import IframeModal from "@/components/Meta2D/IframeModal/index.vue";
import { useSelection } from "@/services/selections";

const { selections } = useSelection();

let { proxy } = getCurrentInstance();

watch(
  () => selections.pen,
  (data) => {
    if (data) {
      let { events } = data;
      if (events) {
        events.some((_: any) => {
          switch (_.action) {
            case 7:
              switch (_.value) {
                case "l-dialog":
                  {
                    meta2d.on(_.value, (e: any) => {
                      if (proxy.$refs.commonModal) {
                        Object.assign(proxy.$refs.commonModal, {
                          visible: true,
                          title: "自定义弹窗",
                        });
                        nextTick(() => {
                          proxy.$refs.commonModal.init(_);
                        });
                      }
                    });
                  }
                  break;
                case "iframe-dialog":
                  {
                    meta2d.on(_.value, (e: any) => {
                      if (proxy.$refs.iframeModal) {
                        Object.assign(proxy.$refs.iframeModal, {
                          visible: true,
                          title: "展示",
                          url: _.params,
                        });
                        nextTick(() => {
                          proxy.$refs.iframeModal.init(e);
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

onMounted(() => {
  // 读取本地存储
  let data: any = localStorage.getItem("meta2d");
  if (data) {
    data = JSON.parse(data);
    data.locked = 1;
    data.rule = false;
    meta2d.open(data);
    // 自适应屏幕显示
    // https://doc.le5le.com/document/119976155
    meta2d.fitView(true, 24);
  }
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