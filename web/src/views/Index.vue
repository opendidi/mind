<!--
 * @Descripttion:
 * @version: 1.0.0
 * @Author: htang
 * @Date: 2023-09-11 08:50:37
 * @LastEditors: htang
 * @LastEditTime: 2025-08-22 10:38:47
-->
<template>
  <div class="app-page">
    <Header />
    <div class="designer">
      <Graphics />
      <a-dropdown
        :trigger="['contextmenu']"
        @visibleChange="handleMenuVisibleChange"
      >
        <Editor />
        <template #overlay>
          <a-menu class="canvas-context-menu" @click="handleMenuClick">
            <template v-for="(vo, idx) in menuLists">
              <template v-if="vo.visible == true">
                <template v-if="vo.title == 'divider'">
                  <a-menu-divider :key="idx" />
                </template>
                <template v-else>
                  <a-menu-item
                    :disabled="vo.disabled"
                    :key="idx"
                    :data="vo.data"
                    :title="vo.title"
                  >
                    <span>{{ vo.title }}</span>
                    <span>{{ vo.keyCode }}</span>
                  </a-menu-item>
                </template>
              </template>
            </template>
          </a-menu>
        </template>
      </a-dropdown>
      <template v-if="activePen && multiPen">
        <Appearance ref="appearance" />
      </template>
      <template v-else>
        <Props :data="propsData" />
      </template>
    </div>
  </div>
</template>

<script lang="ts" setup>
import { ref, nextTick, getCurrentInstance, onMounted, onUnmounted } from "vue";
import type { MenuProps } from "ant-design-vue";
import Header from "@/components/Meta2D/Header/index.vue";
import Graphics from "@/components/Meta2D/Graphics/index.vue";
import Editor from "@/components/Meta2D/Editor/index.vue";
import Props from "@/components/Meta2D/Props/index.vue";
import Appearance from "@/components/Meta2D/Appearance/index.vue";
import { MENUS as menus } from "@/utils/config-contentmenu.ts";
import {
  LOCK_STATE_DATA as lockState,
  PEN_TYPE as PenType,
} from "@/utils/index";
import GET_IMAGE_PATH from "@/utils/graphicGroups.ts";
import { useSelection } from "@/services/selections";
import { useCommonStore, useCommonStoreWithOut } from "@/store/modules/common";

const { proxy } = getCurrentInstance();

const { selections } = useSelection();

let menuLists = ref(menus);

// 选中的画笔状态
let activePen = ref(false);
// 多个画笔状态
let multiPen = ref(false);
// 画笔数组
let pens = ref([]);

let timer: any;

let propsData = ref({});

function save() {
  if (timer) {
    clearTimeout(timer);
  }
  timer = setTimeout(() => {
    const data: any = meta2d.data();
    useCommonStoreWithOut().setTopology(meta2d);
    const commonStore = useCommonStore();
    propsData.value = commonStore.topology.store.data;
    localStorage.setItem("meta2d", JSON.stringify(data));
    timer = undefined;
    commonStore.setIsSave("0");
  }, 500);
}

/**
 * 初始化监听事件
 */
function onInit() {
  // 参考: https://doc.le5le.com/document/138387361#%E6%80%BB%E7%BB%93
  // 缩放画布
  meta2d.on("scale", save);
  // 添加一个/多个画笔
  meta2d.on("add", save);
  // 打开新文件
  meta2d.on("opened", save);
  // 撤销后
  meta2d.on("undo", save);
  // 恢复后
  meta2d.on("redo", save);
  // 添加一个/多个画笔
  meta2d.on("add", save);
  // 删除
  meta2d.on("delete", save);
  // 画笔大小改变
  meta2d.on("resizePens", save);
  // 画笔被旋转
  meta2d.on("rotatePens", save);
  // 移动画笔结束
  meta2d.on("translatePens", save);

  // 记录是否有选中多个图元
  meta2d.on("active", (args: any) => {
    pens.value = args;
    if (args.length >= 1) {
      activePen.value = true;
    }
    if (args.length > 1) {
      multiPen.value = true;
      nextTick(() => {
        proxy.$refs.appearance.init(pens.value);
      });
    } else {
      multiPen.value = false;
    }
    if (args.length == 1) {
      let [pen] = args;
      if (pen["type"] !== undefined) {
        menuLists.value.map((_: any) => {
          switch (pen["type"]) {
            case 0:
              // 节点
              switch (_.data) {
                case "node":
                  {
                    _.visible = false;
                  }
                  break;
                case "line":
                case "penType":
                  {
                    _.visible = true;
                  }
                  break;
              }
              break;
            case 1:
              // 连线
              switch (_.data) {
                case "node":
                case "penType":
                  {
                    _.visible = true;
                  }
                  break;
                case "line":
                  {
                    _.visible = false;
                  }
                  break;
              }
              break;
          }
        });
      }
    }
  });
  // 清空高亮画笔
  meta2d.on("inactive", () => {
    activePen.value = false;
    multiPen.value = false;
    pens.value = [];
  });

  GET_IMAGE_PATH("rotate", "rotate.cur").then((rotateCursor: string) => {
    meta2d.setOptions({
      rotateCursor,
    });
  });
}

/**
 * 处理鼠标右键菜单显示
 */
function handleMenuVisibleChange(e: any) {
  let { pen } = selections;
  if (e) {
    if (pen !== undefined) {
      menuLists.value.some((_: any) => {
        if (_.data == "delete") {
          _.disabled = false;
          _.visible = true;
        }
      });
      switch (pen.locked) {
        case 0:
          menuLists.value.some((_: any) => {
            if (_.data == "locked") {
              _.disabled = false;
            }
            if (_.data == "unlocked") {
              _.disabled = true;
              _.visible = false;
            }
          });
          break;
        case 2:
          menuLists.value.some((_: any) => {
            if (_.data == "locked") {
              _.disabled = true;
              _.visible = false;
            }
            if (_.data == "unlocked") {
              _.disabled = false;
              _.visible = true;
            }
          });
          break;
        default:
          menuLists.value.some((_: any) => {
            if (_.data == "locked") {
              _.disabled = false;
            }
            if (_.data == "unlocked") {
              _.disabled = true;
              _.visible = false;
            }
          });
          break;
      }
      if (pen["children"]) {
        if (pen.children.length !== 0) {
          menuLists.value.map((_: any) => {
            if (_.data == "locked") {
              _.disabled = false;
            }
            if (_.data == "uncombine") {
              _.visible = true;
            }
          });
        }
      }
    } else {
      if (pens.value.length !== 0) {
        menuLists.value.map((_: any) => {
          if (
            ["combine", "delete"].includes(_.data) &&
            activePen.value == true
          ) {
            _.visible = true;
            _.disabled = false;
          }
        });
      }
    }
  } else if (!e) {
    menuLists.value.map((_: any) => {
      switch (_.data) {
        case "combine":
        case "uncombine":
        case "node":
        case "line":
        case "penType":
          _.visible = false;
          break;
        case "delete":
          _.disabled = true;
          break;
      }
    });
  }
}

/**
 * 右键菜单事件集合
 */
const handleMenuClick: MenuProps["onClick"] = (e: any) => {
  let { pen } = selections;
  let list = menuLists.value;
  if (pen || pens.value.length > 0) {
    switch (e.item.data) {
      // 置顶
      case "top":
        meta2d.top(pen);
        break;
      // 置底
      case "bottom":
        meta2d.bottom(pen);
        break;
      // 上一图层
      case "up":
        meta2d.up(pen);
        break;
      // 下一图层
      case "down":
        meta2d.down(pen);
        break;
      // 组合为状态
      case "combine": {
        list.some((_: any) => {
          if (_.data == "combine") {
            _.visible = false;
          }
          if (_.data == "uncombine") {
            _.visible = true;
          }
        });
        if (e.item.title == "组合") {
          meta2d.combine(pens.value);
        } else {
          meta2d.combine(pens.value, 0);
        }
        break;
      }
      // 取消组合为状态
      case "uncombine": {
        list.some((_: any) => {
          if (_.data == "combine") {
            _.visible = true;
          }
          if (_.data == "uncombine") {
            _.visible = false;
          }
        });
        meta2d.uncombine(pen);
        break;
      }
      case "locked": {
        list.some((_: any) => {
          if (_.data == "locked") {
            _.visible = false;
          }
        });
        pens.value.map((_: any) => {
          meta2d.setValue(
            { id: _.id, locked: lockState.DisableMove },
            { render: false }
          );
        });
        break;
      }
      case "unlocked": {
        list.some((_: any) => {
          if (_.data == "locked") {
            _.visible = true;
          }
        });
        pens.value.map((_: any) => {
          meta2d.setValue(
            { id: _.id, locked: lockState.None },
            { render: false }
          );
        });
        break;
      }
      // 删除
      case "delete":
        if (pens.value.length !== 0) {
          meta2d.delete(pens.value);
        }
        break;
      // 剪切
      case "cut":
        if (pens.value.length !== 0) {
          meta2d.cut(pens.value);
        }
        break;
      // 复制
      case "copy":
        if (pens.value.length !== 0) {
          meta2d.copy(pens.value);
        }
        break;
      case "node":
        {
          meta2d.setValue({
            id: pen.id,
            type: PenType.Node,
          });
        }
        break;
      case "line":
        {
          meta2d.setValue({
            id: pen.id,
            type: PenType.Line,
          });
        }
        break;
      default:
        break;
    }
  }
  switch (e.item.data) {
    // 恢复
    case "redo":
      meta2d.redo();
      break;
    // 撤销
    case "undo":
      meta2d.undo();
      break;
    // 粘贴
    case "paste":
      meta2d.paste();
      break;
    default:
      break;
  }
  meta2d.inactive();
  meta2d.render();
  save();
};

onMounted(() => {
  onInit();
});

onUnmounted(() => {
  [
    "scale",
    "add",
    "opened",
    "undo",
    "redo",
    "add",
    "delete",
    "rotatePens",
    "translatePens",
  ].map((_) => {
    meta2d.off(_);
  });
});
</script>

<style lang="less" scoped>
.app-page {
  height: 100vh;
  overflow: hidden;

  .designer {
    display: grid;
    height: calc(100vh - 50px);
    grid-template-columns: 200px 1fr 301px;
  }

  :deep .t-input--auto-width {
    width: 100% !important;
  }

  :deep .ant-form {
    .ant-collapse {
      .ant-collapse-content > .ant-collapse-content-box {
        padding: 6px;
      }

      .ant-form-item {
        margin-bottom: 12px;
      }
    }
  }
}

.canvas-context-menu {
  min-width: 200px;

  :deep .ant-dropdown-menu-title-content {
    display: flex;
    justify-content: space-between;
  }
}
</style>