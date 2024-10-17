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
import { ref, getCurrentInstance, onMounted, onUnmounted } from "vue";
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

const { select } = useSelection();

let { proxy } = getCurrentInstance();

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

  // 按需注册图形库，以下为自带基础图形库
  register(flowPens());
  registerAnchors(flowAnchors());
  register(activityDiagram());
  registerCanvasDraw(activityDiagramByCtx());
  register(classPens());
  register(sequencePens());
  registerCanvasDraw(sequencePensbyCtx());
  registerCanvasDraw(formPens());
  // registerCanvasDraw(chartsPens());
  register(ftaPens());
  registerCanvasDraw(ftaPensbyCtx());
  registerAnchors(ftaAnchors());

  // 初始化插件
  initPlugin();

  // 读取本地存储
  let data: any = localStorage.getItem("meta2d");
  if (data) {
    data = JSON.parse(data);
    // 判断是否为运行查看，是-设置为预览模式
    if (!data.locked) {
      data["locked"] = 0;
    }
    meta2d.open(data);
  }

  setTimeout(() => {
    if (window?.meta2dTools) {
      window?.registerToolsNew();
    }
  }, 1000);

  meta2d.on("active", active);
  meta2d.on("inactive", inactive);

  meta2d.socketFn = (message, context) => {
    if (message) {
      let info = JSON.parse(message);
      if (info.data["data"]) {
        let dataList = JSON.parse(info.data["data"]);
        console.table("数据返回", dataList);
        useCommonStoreWithOut().setVariableData(dataList);
        dataList.map((item) => {
          if (item["dot"] == 0) {
            item["id"] = `a${item["dot"]}`;
          } else {
            item["id"] = item["dot"];
          }
          // 提升机泵液位
          if (item["vtype"] === "FLOAT") {
            let data = parseFloat(item["value"]).toFixed(2);
            item["text"] = Number(data);
            // item['text'] = Number(item['value']);
          } else {
            item["text"] = item["value"];
          }
          if (item["id"] == 6) {
            item["progress"] = item["value"] / 10;
          }
          meta2d.setValue({
            ...item,
          });
        });
      }
    }
    // return false; //表示仅执行自定义的回调函数方法
    return true; //表示除了执行自定义的回调方法外，还会执行核心库方法
  };
});

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