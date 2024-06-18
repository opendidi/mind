<template>
  <div class="graphics">
    <a-tabs
      v-model:activeKey="tabsActiveKey"
      size="small"
      :tabBarGutter="12"
      :centered="true"
    >
      <a-tab-pane key="1" tab="系统组件">
        <div class="p-3">
          <a-input
            v-model:value="keyword"
            placeholder="搜索"
            @input="filterGraphicGroups"
            :disabled="activeKey == 2 ? true : false"
          />
        </div>
        <div class="scroll">
          <a-collapse
            v-model:activeKey="activeKey"
            :defaultExpandAll="true"
            expand-icon-position="right"
            accordion
            ghost
            :destroyInactivePanel="true"
          >
            <template v-for="(item, idx) in graphicGroupsList" :key="idx">
              <a-collapse-panel :forceRender="true" v-show="item.show">
                <template #header>
                  <div class="flex items-center">
                    <template v-if="activeKey == idx">
                      <folder-open-outlined style="margin: 0 6px 0 0" />
                    </template>
                    <template v-else>
                      <folder-outlined style="margin: 0 6px 0 0" />
                    </template>
                    <a-tooltip placement="right">
                      <template #title>
                        <span>{{ item.name }}</span>
                      </template>
                      <span class="group-name" :title="item.name">
                        {{ item.name }}
                      </span>
                    </a-tooltip>
                    <span class="group-total">
                      {{ "(" + item.list.length + ")" }}
                    </span>
                  </div>
                </template>
                <ul class="flex items-center flex-wrap">
                  <template v-for="(vo, i) in item.list" :key="i">
                    <li
                      class="graphic"
                      :draggable="true"
                      @dragstart="dragStart($event, vo)"
                      @click.prevent="dragStart($event, vo)"
                      :title="vo.data.label"
                    >
                      <template v-if="vo.icon.indexOf('iconfont') !== -1">
                        <i :class="vo.icon"></i>
                      </template>
                      <template
                        v-else-if="vo.icon.indexOf('video-camera') !== -1"
                      >
                        <Icon
                          :title="vo.name"
                          :name="vo.icon"
                          style="font-size: 30px"
                        />
                      </template>
                      <template v-else-if="vo.data.image">
                        <img
                          :src="vo.data.image"
                          alt=""
                          :title="vo.data.label"
                        />
                      </template>
                      <template v-else-if="vo.subClassName == '箭头'">
                        <div
                          class="flex items-center justify-center"
                          v-html="vo.svg"
                        ></div>
                      </template>
                      <template v-else-if="vo.subClassName == '拓扑图未分类'">
                        <div
                          class="flex items-center justify-center"
                          v-html="vo.svg"
                        ></div>
                      </template>
                      <template v-else>
                        <svg class="l-icon" aria-hidden="true">
                          <use :xlink:href="'#' + vo.icon"></use>
                        </svg>
                      </template>
                    </li>
                  </template>
                </ul>
              </a-collapse-panel>
            </template>
          </a-collapse>
        </div>
        <div class="more-graphical flex justify-center items-center">
          <a-button @click="openGraphics">
            <template #icon>
              <AppstoreOutlined />
            </template>
            图形库管理
          </a-button>
        </div>
      </a-tab-pane>
      <a-tab-pane key="2" tab="我的组件" force-render>
        <div class="mkdir-head" @click="directoryVisible = true">
          <folder-add-outlined />
          <span>新建文件夹</span>
        </div>
        <div class="">
          <a-collapse
            v-model:activeKey="directoryKey"
            :defaultExpandAll="true"
            expand-icon-position="right"
            accordion
            ghost
            :destroyInactivePanel="true"
          >
            <template v-for="(vo, idx) in directoryList" :key="idx">
              <a-collapse-panel :forceRender="true">
                <template #header>
                  <span>{{ vo.name }}</span>
                </template>
              </a-collapse-panel>
            </template>
          </a-collapse>
        </div>
      </a-tab-pane>
    </a-tabs>
    <MoreModal ref="moreModal" @oks="heandleGraphicGroups" />
  </div>
</template>

<script lang="ts" setup>
import { ref, watch, nextTick, onMounted, getCurrentInstance } from "vue";
import {
  FolderOutlined,
  FolderOpenOutlined,
  FolderAddOutlined,
  AppstoreOutlined,
} from "@ant-design/icons-vue";
import { GRAPHIC_GROUPS as graphicGroups } from "@/utils/graphicGroups.ts";
import MoreModal from "./components/more-modal.vue";
import { useCommonStore } from "@/store/modules/common";
import { Icon } from "tdesign-icons-vue-next";

// 原数据
let originalGraphicGroups = graphicGroups;

let graphicGroupsList = ref(graphicGroups);

let { proxy } = getCurrentInstance();

let tabsActiveKey = ref("1");

let activeKey = ref(0);

let directoryVisible = ref(false);

// 文件夹名称
let directoryName = ref("");

// 文件夹列表
let directoryList = ref([]);

// 折叠key
let directoryKey = ref("");

// 过滤值
let keyword = ref("");

watch(
  () => directoryVisible.value,
  (bool: boolean) => {
    if (!bool) {
      directoryName.value = "";
    }
  }
);

const dragStart = (e: any, elem: any) => {
  if (!elem) {
    return;
  }
  e.stopPropagation();

  // 拖拽事件
  if (e instanceof DragEvent) {
    // 设置拖拽数据
    e.dataTransfer?.setData("Meta2d", JSON.stringify(elem.data));
  } else {
    // 支持单击添加图元。平板模式
    meta2d.canvas.addCaches = [elem.data];
  }
};

function openGraphics() {
  proxy.$refs.moreModal.visible = true;
  nextTick(() => {
    proxy.$refs.moreModal.init();
  });
}

/**
 * 获取文件夹名称
 */
function handleOk() {
  directoryList.value.push({
    name: directoryName.value,
  });
  directoryVisible.value = false;
}

/**
 * 显示/隐藏回调后处理左侧栏是否显示或者隐藏
 */
function heandleGraphicGroups() {
  let graphicsKey = useCommonStore().graphics;
  let keys = Object.keys(graphicsKey);
  let array: any = [];
  Object.values(graphicsKey).map((_, idx) => {
    if (!_) {
      array.push(keys[idx]);
    }
  });
  graphicGroupsList.value.map((_) => {
    if (array.includes(_.name)) {
      _.show = false;
    } else {
      _.show = true;
    }
  });
}

/**
 * 筛选过滤组件
 */
function filterGraphicGroups() {
  let key = keyword.value;
  if (key) {
    let list = originalGraphicGroups;
    let array: any = [];
    for (let i = 0; i < list.length; i++) {
      if (list[i].name.indexOf(key) !== -1) {
        array.push({
          ...list[i],
        });
      }
      const foundInList = list[i].list.filter((item: any) => {
        let { name } = item;
        if (name.indexOf("http") !== -1) {
          const decodedStr = decodeURIComponent(name);
          if (decodedStr.indexOf(key) !== -1) {
            return item;
          }
        } else {
          if (name.indexOf(key) !== -1) {
            return item;
          }
        }
      });
      if (foundInList.length !== 0) {
        array.push({
          ...list[i],
          list: [...foundInList],
        });
      }
    }
    graphicGroupsList.value = array;
  } else {
    graphicGroupsList.value = graphicGroups;
  }
}

heandleGraphicGroups();
</script>

<style lang="less" scoped>
.graphics {
  height: calc(100vh - 40px);
  background: #fff;
  border-right: 1px solid #dddddd;
  z-index: 2;

  :deep(.ant-tabs) {
    .ant-tabs-nav {
      margin-bottom: 0;
    }

    .mkdir-head {
      margin: 12px;

      .anticon {
        margin: 0 6px 0 0;
      }

      &:hover {
        color: #1890ff;
        cursor: pointer;
      }
    }
  }

  .scroll {
    height: calc(100vh - 188px);
    overflow-y: auto;
    // &::-webkit-scrollbar {
    //   width: 8px;
    //   height: 10px;
    //   background: transparent;
    // }
    // &::-webkit-scrollbar-thumb {
    //   background-color: #ddd;
    //   border-radius: 4px;
    // }
  }

  .more-graphical {
    height: 54px;
    border-top: 1px solid #e5e5e5;
    box-sizing: border-box;
  }
  :deep .ant-collapse {
    border-top: none;
    .ant-collapse-item {
      .ant-collapse-header {
        span {
        }
        .group-name {
          display: inline-block;
          max-width: 95px;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }
        .group-total {
          flex: 1;
        }
      }
    }
    .ant-collapse-content-box {
      padding: 3px;
      ul {
        padding: 0;
        margin: 0;
        list-style: none;
        .graphic {
          position: relative;
          width: 25%;
          height: 25%;
          padding: 6px;
          border-radius: 2px;
          border: 1px solid transparent;
          box-sizing: border-box;
          img {
            display: block;
            margin: 0 auto;
            max-width: 100px;
            max-height: 25px;
          }
          .iconfont {
            display: block;
            font-size: 28px;
            text-align: center;
          }

          &:hover {
            cursor: pointer;
            border-color: var(--color-primary);
          }

          p {
            display: -webkit-box;
            margin-top: 6px;
            padding: 0 8px;
            text-align: center;
            font-size: 12px;
            height: 12px;
            line-height: 1;
            overflow: hidden;
            text-overflow: ellipsis;
            -webkit-line-clamp: 1;
            word-break: break-all;
            -webkit-box-orient: vertical;
          }

          .l-icon {
            height: 28px;
            width: 100%;
            margin: auto;
            color: var(--color);
          }
        }
      }
    }
  }
}
</style>