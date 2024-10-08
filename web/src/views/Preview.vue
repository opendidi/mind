<!--
 * @Descripttion:
 * @version: 1.0.0
 * @Author: htang
 * @Date: 2023-09-11 08:50:37
 * @LastEditors: htang
 * @LastEditTime: 2024-04-10 16:03:12
-->
<template>
  <div class="app-page">
    <Editor />
    <!-- 弹窗 -->
    <CommonModal ref="commonModal" :width="'90vw'" />
    <!-- 小窗展示 -->
    <IframeModal ref="iframeModal" />
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
}
</style>