<!--
 * @Descripttion:
 * @version: 1.0.0
 * @Author: htang
 * @Date: 2023-11-07 19:56:27
 * @LastEditors: htang
 * @LastEditTime: 2024-10-09 14:59:20
-->
<template>
  <div id="meta2d"></div>
</template>

<script lang="ts" setup>
import { ref, getCurrentInstance, onMounted, onUnmounted, watch } from "vue";
import { useRoute } from "vue-router";
import { provideCanvas } from "@/composables/useCanvas";
import { message } from "ant-design-vue";
import { apiBlueprintFind } from "@/api/blueprint";
import * as echarts from "echarts";
import { register as registerEcharts } from "@meta2d/chart-diagram";
import { flowPens, flowAnchors } from "@meta2d/flow-diagram";
import {
  activityDiagram,
  activityDiagramByCtx,
} from "@meta2d/activity-diagram";
import { classPens } from "@meta2d/class-diagram";
import { sequencePens, sequencePensbyCtx } from "@meta2d/sequence-diagram";
import { formPens } from "@meta2d/form-diagram";
import { ftaPens, ftaPensbyCtx, ftaAnchors } from "@meta2d/fta-diagram";
import {
  Meta2d,
  register,
  registerAnchors,
  registerCanvasDraw,
} from "@meta2d/core";
import { CollapseChildPlugin } from "mind-plugins-collapse";
import { useCommonStoreWithOut } from "@/store/modules/common";
import { removeOriginalData } from "@/utils/meta-storage";
import "@/assets/js/assets.le5lecdn.com_2d_canvas2svg.js";
import "@/assets/js/arrows.js";
import "@/assets/js/rg.js";
import { MetaPlugin } from "@/utils/plugin";
import { mindBoxPlugin } from "@meta2d/plugin-mind-core";
import { useSelection } from "@/services/selections";
import { useKeyboardShortcuts } from "@/composables/useKeyboardShortcuts";

const { select } = useSelection();

let { proxy } = getCurrentInstance();

let onStorageChange: ((e: StorageEvent) => void) | null = null;

const route = useRoute();

function loadBlueprint(id: string) {
  const meta2d = (window as any).meta2d;
  if (!meta2d) return;
  apiBlueprintFind({ id }).then((res: any) => {
    if (res?.data) {
      const bp = res.data;
      const canvasData: any = { name: bp.name || '', pens: bp.pens || [], lines: [] };
      if (bp.background) canvasData.background = bp.background;
      if (bp.grid !== undefined) canvasData.grid = bp.grid;
      if (bp.gridColor) canvasData.gridColor = bp.gridColor;
      if (bp.gridSize) canvasData.gridSize = bp.gridSize;
      if (bp.rule !== undefined) canvasData.rule = bp.rule;
      if (bp.ruleColor) canvasData.ruleColor = bp.ruleColor;
      if (!canvasData.locked) canvasData.locked = 0;
      meta2d.open(canvasData);
      window.dispatchEvent(new CustomEvent('meta2d:dataLoaded'));
    } else {
      message.error("图纸加载失败");
    }
  }).catch(() => {
    message.error("图纸加载失败");
  });
}

onMounted(() => {
  const meta2dOptions: any = {
    background: "transparent",
  };
  if (window.location.pathname.indexOf("preview") !== -1) {
    meta2dOptions["rule"] = false;
  } else {
    meta2dOptions["rule"] = true;
  }
  let meta2d = new Meta2d("meta2d", meta2dOptions);
  provideCanvas(meta2d);

  // Register keyboard shortcuts (Delete, Ctrl+C/V/A/D, arrows, Escape)
  useKeyboardShortcuts(meta2d);

  // 按需注册图形库，以下为自带基础图形库
  register(flowPens());
  registerAnchors(flowAnchors());
  register(activityDiagram());
  registerCanvasDraw(activityDiagramByCtx());
  register(classPens());
  register(sequencePens());
  registerCanvasDraw(sequencePensbyCtx());
  registerCanvasDraw(formPens());
  register(ftaPens());
  registerCanvasDraw(ftaPensbyCtx());
  registerAnchors(ftaAnchors());

  // 注册 ECharts 图表画笔
  registerEcharts(echarts);

  // 初始化插件
  initPlugin();

  // 加载数据：有 ID 从后端加载，无 ID 新建空白画布
  const blueprintId = route.query.id as string | undefined;
  if (blueprintId) {
    loadBlueprint(blueprintId);
  }

  // Register custom tools immediately — meta2dTools is already available
  // from synchronously loaded arrows.js and canvas2svg.js
  if (window?.meta2dTools) {
    window?.registerToolsNew();
  }

  // Cross-tab sync: reload canvas when another tab (e.g. chat) modifies localStorage
  onStorageChange = (e: StorageEvent) => {
    if (e.key === 'meta2d' && e.newValue) {
      try {
        const data = JSON.parse(e.newValue);
        if (!data.locked) data.locked = 0;
        meta2d.open(data);
        window.dispatchEvent(new CustomEvent('meta2d:dataLoaded'));
      } catch { /* ignore malformed data */ }
    }
  };
  window.addEventListener('storage', onStorageChange);

  meta2d.on("active", active);
  meta2d.on("inactive", inactive);

  meta2d.socketFn = (message, context) => {
    if (message) {
      let info = typeof message === 'string' ? JSON.parse(message) : message;
      if (info.data["data"]) {
        let raw = info.data["data"];
        let dataList = typeof raw === 'string' ? JSON.parse(raw) : raw;
        let hasUpdate = false;
        dataList.forEach((item: any) => {
          if (item["dot"] == 0) {
            item["id"] = `a${item["dot"]}`;
          } else {
            item["id"] = item["dot"];
          }
          if (item["vtype"] === "FLOAT") {
            let data = parseFloat(item["value"]).toFixed(2);
            item["text"] = Number(data);
          } else {
            item["text"] = item["value"];
          }
          if (item["id"] == 6) {
            item["progress"] = item["value"] / 10;
          }
          meta2d.setValue({ ...item }, { render: false });
          hasUpdate = true;
        });
        if (hasUpdate) {
          meta2d.render();
          // Sync to localStorage so data persists across refresh
          localStorage.setItem('meta2d', JSON.stringify(meta2d.data()));
          // Store variable data for binding UI (updates store + localStorage)
          useCommonStoreWithOut().setVariableData(dataList);
          // Mark save state as dirty
          useCommonStoreWithOut().setIsSave("0");
        }
      }
    }
    return true;
  };
});

// 监听路由变化，切换图纸
watch(
  () => route.query.id,
  (newId) => {
    if (newId && typeof newId === 'string') {
      loadBlueprint(newId);
    }
  }
);

function active(pens?: Pen[]) {
  select(pens);
}

function inactive() {
  select();
}

/**
 * 初始化插件
 */
function initPlugin() {
  let target = "mindNode";
  let metaplugin = new MetaPlugin({});
  metaplugin.initPlugin(meta2d, target, {});
}

onUnmounted(() => {
  if (onStorageChange) window.removeEventListener('storage', onStorageChange);
  meta2d.destroy();
  // 取消订阅
  meta2d.off("active", active);
  meta2d.off("inactive", inactive);
  // 删除原始数据
  removeOriginalData();
});
</script>

<style lang="less" scoped>
#meta2d {
  position: relative;
  width: 100%;
  height: 100%;
  .toolbox {
    position: absolute;
    display: none;
    width: 100px;
    height: 30px;
    background: red;
    z-index: 10000;
  }
}
</style>