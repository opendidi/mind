<template>
  <div class="app-header flex items-center justify-between">
    <div class="head-left flex items-center">
      <a-dropdown>
        <a class="ant-dropdown-link flex items-center flex-col">
          <t-icon name="file" />
          <span>文件</span>
        </a>
        <template #overlay>
          <a-menu>
            <!-- <a-menu-item @click="newFile">
              <a>新建文件</a>
            </a-menu-item> -->
            <!-- <a-menu-item @click="openFile" divider="true">
              <a>打开文件</a>
            </a-menu-item> -->
            <a-menu-item divider="true">
              <a @click="downloadJson">下载JSON文件</a>
            </a-menu-item>
            <a-menu-item>
              <a @click="downloadPng">下载为PNG</a>
            </a-menu-item>
            <a-menu-item>
              <a @click="downloadSvg">下载为SVG</a>
            </a-menu-item>
          </a-menu>
        </template>
      </a-dropdown>
      <a-dropdown>
        <a class="ant-dropdown-link flex items-center flex-col">
          <t-icon name="edit-1" />
          <span>编辑</span>
        </a>
        <template #overlay>
          <a-menu>
            <a-menu-item>
              <a @click="onToggleAnchorMode">
                <div class="flex">增加/删除锚点</div>
              </a>
            </a-menu-item>
            <a-menu-item>
              <a @click="onAddAnchorHand">
                <div class="flex">添加手柄</div>
              </a>
            </a-menu-item>
            <a-menu-item>
              <a @click="onRemoveAnchorHand">
                <div class="flex">删除手柄</div>
              </a>
            </a-menu-item>
          </a-menu>
        </template>
      </a-dropdown>
      <a class="flex items-center flex-col" @click="onSave(true)">
        <t-icon name="save" />
        <span>保存</span>
      </a>
    </div>
    <div class="head-center flex items-center">
      <a
        class="flex items-center flex-col"
        :class="[isOnDrawLine == true ? 'active' : '']"
        @click="onDrawLine"
      >
        <t-icon name="pen" />
        <span>钢笔</span>
      </a>
      <a
        class="flex items-center flex-col"
        :class="[isDrawingPencil == true ? 'active' : '']"
        @click="onDrawingPencil"
      >
        <t-icon name="edit" />
        <span>铅笔</span>
      </a>
      <a
        class="flex items-center flex-col"
        :class="[isShowMagnifier == true ? 'active' : '']"
        @click="onShowMagnifier"
      >
        <t-icon name="search" />
        <span>放大镜</span>
      </a>
      <a class="flex items-center flex-col" @click="onUndo">
        <t-icon name="rollback" />
        <span>撤销</span>
      </a>
      <a class="flex items-center flex-col" @click="onRedo">
        <t-icon name="rollfront" />
        <span>重做</span>
      </a>
      <a
        class="flex items-center flex-col"
        @dragstart="onAddShape($event, 'line')"
        @click="onAddShape($event, 'line')"
      >
        <t-icon name="remove" />
        <span>直线</span>
      </a>
      <a
        class="flex items-center flex-col"
        @dragstart="onAddShape($event, 'text')"
        @click="onAddShape($event, 'text')"
      >
        <t-icon name="textbox" />
        <span>文字</span>
      </a>
      <!-- <a class="flex items-center" @click="drawLine">
        <svg
          width="1em"
          height="1em"
          viewBox="0 0 1024 1024"
          xmlns="http://www.w3.org/2000/svg"
          :style="{
            color: isDrawLine ? ' #1677ff' : '',
          }"
        >
          <path
            d="M192 64a128 128 0 0 1 123.968 96H384a160 160 0 0 1 159.68 149.504L544 320v384a96 96 0 0 0 86.784 95.552L640 800h68.032a128 128 0 1 1 0 64.064L640 864a160 160 0 0 1-159.68-149.504L480 704V320a96 96 0 0 0-86.784-95.552L384 224l-68.032 0.064A128 128 0 1 1 192 64z m640 704a64 64 0 1 0 0 128 64 64 0 0 0 0-128zM192 128a64 64 0 1 0 0 128 64 64 0 0 0 0-128z"
            fill="currentColor"
          ></path>
        </svg>
        <span>连线</span>
      </a> -->
      <a-dropdown v-model:visible="lineWidthVisible">
        <a class="flex items-center flex-col">
          <span class="flex items-center">
            {{ data.lineWidth }}&nbsp;
            <t-icon name="chevron-down-s" />
          </span>
          <span>线宽</span>
        </a>
        <template #overlay>
          <a-menu style="width: 220px">
            <a-menu-item key="1">
              <a-input-number
                v-model:value="data.lineWidth"
                style="width: 100%"
                @blur="getDataLineWidth"
              />
            </a-menu-item>
          </a-menu>
        </template>
      </a-dropdown>
      <a-dropdown overlayClassName="header-dropdown">
        <a class="flex items-center flex-col">
          <span class="flex items-center">
            <svg class="l-icon" aria-hidden="true">
              <use
                :xlink:href="
                  lineTypes.find((item) => item.value === currentLineType)?.icon
                "
              ></use>
            </svg>
            <t-icon name="chevron-down-s" />
          </span>
          <span>连线</span>
        </a>
        <template #overlay>
          <a-menu style="width: 160px">
            <template v-for="(item, idx) in lineTypes" :key="idx">
              <a-menu-item>
                <div class="flex middle" @click="changeLineType(item.value)">
                  {{ item.name }} <span class="flex-grow"></span>
                  <svg class="l-icon" aria-hidden="true">
                    <use :xlink:href="item.icon"></use>
                  </svg>
                </div>
              </a-menu-item>
            </template>
          </a-menu>
        </template>
      </a-dropdown>
      <a-dropdown overlayClassName="header-dropdown">
        <a class="flex items-center flex-col">
          <span class="flex items-center">
            <svg class="l-icon" aria-hidden="true">
              <use
                :xlink:href="
                  fromArrows.find((item) => item.value === fromArrow)?.icon
                "
              ></use>
            </svg>
            <t-icon name="chevron-down-s" />
          </span>
          <span>起点</span>
        </a>
        <template #overlay>
          <a-menu style="width: 160px">
            <template v-for="(item, idx) in fromArrows" :key="idx">
              <a-menu-item>
                <div
                  class="flex middle"
                  style="height: 30px"
                  @click="changeFromArrow(item.value)"
                >
                  <svg class="l-icon" aria-hidden="true">
                    <use :xlink:href="item.icon"></use>
                  </svg>
                </div>
              </a-menu-item>
            </template>
          </a-menu>
        </template>
      </a-dropdown>
      <a-dropdown overlayClassName="header-dropdown">
        <a class="flex items-center flex-col">
          <span class="flex items-center">
            <svg class="l-icon" aria-hidden="true">
              <use
                :xlink:href="
                  toArrows.find((item) => item.value === toArrow)?.icon
                "
              ></use>
            </svg>
            <t-icon name="chevron-down-s" />
          </span>
          <span>终点</span>
        </a>
        <template #overlay>
          <a-menu style="width: 160px">
            <template v-for="(item, idx) in toArrows" :key="idx">
              <a-menu-item>
                <div
                  class="flex middle"
                  style="height: 30px"
                  @click="changeToArrow(item.value)"
                >
                  <svg class="l-icon" aria-hidden="true">
                    <use :xlink:href="item.icon"></use>
                  </svg>
                </div>
              </a-menu-item>
            </template>
          </a-menu>
        </template>
      </a-dropdown>
      <a
        class="flex items-center flex-col"
        :class="[isAutoAnchor == true ? 'active' : '']"
        @click="onAutoAnchor"
      >
        <t-icon name="focus" />
        <span>自动锚点</span>
      </a>
      <a
        class="flex items-center flex-col"
        :class="[isDisableAnchor == true ? 'active' : '']"
        @click="onDisableAnchor"
      >
        <t-icon name="map-aiming" />
        <span>
          {{ isDisableAnchor ? "显示锚点" : "禁用锚点" }}
        </span>
      </a>
    </div>
    <div class="head-right flex items-center">
      <a
        class="flex items-center flex-col"
        @click="setLocked"
        :style="{
          color: data.locked == 1 ? '#faad14' : data.locked == 2 ? 'red' : '',
        }"
      >
        <template v-if="data.locked == 0">
          <t-icon name="lock-off" />
          <span>编辑</span>
        </template>
        <template v-if="data.locked == 1">
          <t-icon name="lock-on" />
          <span>预览</span>
        </template>
        <template v-if="data.locked == 2">
          <t-icon name="lock-on" />
          <span>锁定</span>
        </template>
      </a>
      <a class="flex items-center flex-col" @click="onView()" title="运行查看">
        <t-icon name="play-circle" />
        <span>预览</span>
      </a>
      <template v-if="scale > 0">
        <a class="flex items-center flex-col">
          <span>{{ scale }}%</span>
          <span>视图</span>
        </a>
      </template>
      <a-tooltip title="100%视图" placement="bottom">
        <a class="flex items-center flex-col" @click="onScaleDefault">
          <t-icon name="refresh" />
          <span>还原</span>
        </a>
      </a-tooltip>
      <a
        class="flex items-center flex-col"
        @click="onScaleWindow"
        title="窗口大小"
      >
        <t-icon name="fullscreen-exit" />
        <span>窗口大小</span>
      </a>
      <a
        class="flex items-center flex-col"
        title="文件管理"
        @click="openFileManager"
      >
        <t-icon name="folder-open" />
        <span>文件管理</span>
      </a>
      <a class="flex items-center flex-col" @click="onSearch">
        <t-icon name="share" />
        <span>分享</span>
      </a>
      <a
        class="flex items-center flex-col"
        href="https://github.com/opendidi/mind"
        target="_blank"
      >
        <t-icon name="logo-github" />
        <span>源代码</span>
      </a>
    </div>
    <ShareModal ref="shareModal" />
    <FileManager ref="fileManager" :mode="'multiple'" />
  </div>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import { Icon } from "tdesign-vue-next";
import { GithubOutlined } from "@ant-design/icons-vue";
export default defineComponent({
  components: {
    GithubOutlined,
    "t-icon": Icon,
  },
});
</script>

<script lang="ts" setup>
import { onMounted, reactive, ref, getCurrentInstance, nextTick } from "vue";
import { useRouter } from "vue-router";
import { Pen, PenType, deepClone } from "@meta2d/core";
import FileSaver from "file-saver";
import { message } from "ant-design-vue";
import { CaretDownOutlined } from "@ant-design/icons-vue";
import ShareModal from "../Share/index.vue";
import { Icon } from "tdesign-vue-next";
import { useCommonStore, useCommonStoreWithOut } from "@/store/modules/common";
import FileManager from "@/components/FileManager/index.vue";

let { proxy } = getCurrentInstance();

const router = useRouter();

let data = ref({});

// 原始数据
let originalData = ref({});

let isOnDrawLine = ref(false);

let isDrawingPencil = ref<boolean>(false);

// 连线时，自动选中节点锚点
let isAutoAnchor = ref<boolean>(false);

// 禁止显示锚点
let isDisableAnchor = ref<boolean>(false);

// 是否开启放大镜
let isShowMagnifier = ref<boolean>(false);

const isDrawLine = ref<boolean>(false);

const scale = ref(0);

let lineWidthVisible = ref(false);

onMounted(() => {
  const timer = setInterval(() => {
    if (meta2d) {
      data.value = meta2d.store.data;
      if (meta2d.store.data["lineWidth"] == undefined) {
        meta2d.store.data["lineWidth"] = 1;
        meta2d.setValue({
          lineWidth: 1,
        });
      }
      clearInterval(timer);
      // 获取初始缩放比例
      scaleSubscriber(meta2d.store.data.scale);
      // 监听缩放
      meta2d.on("scale", scaleSubscriber);
      let options: any = meta2d.getOptions();
      // 自动锚点
      isAutoAnchor.value = options.autoAnchor;
    }
  }, 200);
});

function scaleSubscriber(val: number) {
  scale.value = Math.round(val * 100);
}

const drawLine = () => {
  if (isDrawLine.value) {
    isDrawLine.value = false;
    meta2d.finishDrawLine();
    meta2d.drawLine();
    meta2d.store.options.disableAnchor = true;
  } else {
    isDrawLine.value = true;
    meta2d.drawLine(meta2d.store.options.drawingLineName);
    meta2d.store.options.disableAnchor = false;
  }
};

const lineTypes = reactive([
  { name: "曲线", icon: "#l-curve2", value: "curve" },
  { name: "线段", icon: "#l-polyline", value: "polyline" },
  { name: "直线", icon: "#l-line", value: "line" },
  { name: "脑图曲线", icon: "#l-mind", value: "mind" },
]);
const currentLineType = ref("curve");

const changeLineType = (value: string) => {
  currentLineType.value = value;
  if (meta2d) {
    meta2d.store.options.drawingLineName = value;
    meta2d.canvas.drawingLineName && (meta2d.canvas.drawingLineName = value);
    meta2d.store.active?.forEach((pen) => {
      meta2d.updateLineType(pen, value);
    });
  }
};

/**
 * 获取线宽
 */
function getDataLineWidth() {
  if (data.value["lineWidth"]) {
    meta2d.setValue({
      lineWidth: data.value.lineWidth,
    });
    useCommonStoreWithOut().setTopology(meta2d);
  }
}

const fromArrow = ref("");
const fromArrows = [
  { icon: "#l-line", value: "" },
  { icon: "#l-from-triangle", value: "triangle" },
  { icon: "#l-from-diamond", value: "diamond" },
  { icon: "#l-from-circle", value: "circle" },
  { icon: "#l-from-lineDown", value: "lineDown" },
  { icon: "#l-from-lineUp", value: "lineUp" },
  { icon: "#l-from-triangleSolid", value: "triangleSolid" },
  { icon: "#l-from-diamondSolid", value: "diamondSolid" },
  { icon: "#l-from-circleSolid", value: "circleSolid" },
  { icon: "#l-from-line", value: "line" },
];
const toArrow = ref("");
const toArrows = [
  { icon: "#l-line", value: "" },
  { icon: "#l-to-triangle", value: "triangle" },
  { icon: "#l-to-diamond", value: "diamond" },
  { icon: "#l-to-circle", value: "circle" },
  { icon: "#l-to-lineDown", value: "lineDown" },
  { icon: "#l-to-lineUp", value: "lineUp" },
  { icon: "#l-to-triangleSolid", value: "triangleSolid" },
  { icon: "#l-to-diamondSolid", value: "diamondSolid" },
  { icon: "#l-to-circleSolid", value: "circleSolid" },
  { icon: "#l-to-line", value: "line" },
];

const changeFromArrow = (value: string) => {
  fromArrow.value = value;
  // 画布默认值
  meta2d.store.data.fromArrow = value;
  // 活动层的箭头都变化
  if (meta2d.store.active) {
    meta2d.store.active.forEach((pen: Pen) => {
      if (pen.type === PenType.Line) {
        pen.fromArrow = value;
        meta2d.setValue(
          {
            id: pen.id,
            fromArrow: pen.fromArrow,
          },
          {
            render: false,
          }
        );
      }
    });
    meta2d.render();
  }
};

const changeToArrow = (value: string) => {
  toArrow.value = value;
  // 画布默认值
  meta2d.store.data.toArrow = value;
  // 活动层的箭头都变化
  if (meta2d.store.active) {
    meta2d.store.active.forEach((pen: Pen) => {
      if (pen.type === PenType.Line) {
        pen.toArrow = value;
        meta2d.setValue(
          {
            id: pen.id,
            toArrow: pen.toArrow,
          },
          {
            render: false,
          }
        );
      }
    });
    meta2d.render();
  }
};

const newFile = () => {
  meta2d.open({ name: "新建项目", pens: [] } as any);
};

function readFile(file: Blob) {
  return new Promise<string>((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      resolve(reader.result as string);
    };
    reader.onerror = reject;
    reader.readAsText(file);
  });
}

function openFile() {
  // 1. 显示选择文件对话框
  const input = document.createElement("input");
  input.type = "file";
  input.onchange = async (event) => {
    const elem = event.target as HTMLInputElement;
    if (elem.files && elem.files[0]) {
      // 2. 读取文件字符串内容
      const text = await readFile(elem.files[0]);
      try {
        // 3. 打开文件内容
        meta2d.open(JSON.parse(text));

        // 可选：缩放到窗口大小展示
        meta2d.fitView();
      } catch (e) {
        console.log(e);
      }
    }
  };
  input.click();
}

const downloadJson = () => {
  const data: any = meta2d.data();
  FileSaver.saveAs(
    new Blob([JSON.stringify(data)], {
      type: "text/plain;charset=utf-8",
    }),
    `${data.name || "test"}.json`
  );
};

const downloadPng = () => {
  let name = (meta2d.store.data as any).name;
  if (name) {
    name += ".png";
  }
  meta2d.downloadPng(name);
};

// 判断该画笔 是否是组合为状态中 展示的画笔
function isShowChild(pen: any, store: any) {
  let selfPen = pen;
  while (selfPen && selfPen.parentId) {
    const oldPen = selfPen;
    selfPen = store.pens[selfPen.parentId];
    const showChildIndex = selfPen?.calculative?.showChild;
    if (showChildIndex != undefined) {
      const showChildId = selfPen.children[showChildIndex];
      if (showChildId !== oldPen.id) {
        return false;
      }
    }
  }
  return true;
}

function downloadSvg() {
  if (!C2S) {
    message.error("请先加载canvas2svg.js插件");
    return;
  }

  const rect: any = meta2d.getRect();
  rect.x -= 10;
  rect.y -= 10;
  const ctx = new C2S(rect.width + 20, rect.height + 20);
  ctx.textBaseline = "middle";
  for (const pen of meta2d.store.data.pens) {
    if (pen.visible == false || !isShowChild(pen, meta2d.store)) {
      continue;
    }
    meta2d.renderPenRaw(ctx, pen, rect);
  }

  let mySerializedSVG = ctx.getSerializedSvg();
  if (meta2d.store.data.background) {
    mySerializedSVG = mySerializedSVG.replace("{{bk}}", "");
    mySerializedSVG = mySerializedSVG.replace(
      "{{bkRect}}",
      `<rect x="0" y="0" width="100%" height="100%" fill="${meta2d.store.data.background}"></rect>`
    );
  } else {
    mySerializedSVG = mySerializedSVG.replace("{{bk}}", "");
    mySerializedSVG = mySerializedSVG.replace("{{bkRect}}", "");
  }

  mySerializedSVG = mySerializedSVG.replace(/--le5le--/g, "&#x");

  const urlObject: any = (window as any).URL || window;
  const export_blob = new Blob([mySerializedSVG]);
  const url = urlObject.createObjectURL(export_blob);

  const a = document.createElement("a");
  a.setAttribute(
    "download",
    `${(meta2d.store.data as any).name || "le5le.meta2d"}.svg`
  );
  a.setAttribute("href", url);
  const evt = document.createEvent("MouseEvents");
  evt.initEvent("click", true, true);
  a.dispatchEvent(evt);
}

function onUndo() {
  meta2d.undo();
}

function onRedo() {
  meta2d.redo();
}

function onCut() {
  meta2d.cut();
}

function onCopy() {
  meta2d.copy();
}

function onPaste() {
  meta2d.paste();
}

function onAll() {
  meta2d.activeAll();
}

function onDelete() {
  meta2d.delete();
}

function onAddShape(event: DragEvent | MouseEvent, name: string) {
  event.stopPropagation();
  let data: any;
  switch (name) {
    case "text":
      // 构建一个文本图元
      data = {
        text: "text",
        width: 100,
        height: 20,
        name: "text",
      };
      break;
    case "line":
      // 构建一个直线图元
      data = {
        anchors: [
          { id: "0", x: 1, y: 0 },
          { id: "1", x: 0, y: 1 },
        ],
        width: 100,
        height: 100,
        name: "line",
        lineName: "line",
        type: 1,
      };
      break;
  }
  if (!(event as DragEvent).dataTransfer) {
    // 支持点击画布添加
    meta2d.canvas.addCaches = deepClone([data]);
  } else {
    // 支持拖拽添加
    (event as DragEvent).dataTransfer?.setData("Meta2d", JSON.stringify(data));
  }
}

const onScaleDefault = () => {
  meta2d.scale(1);
  meta2d.centerView();
};

const onScaleWindow = () => {
  meta2d.fitView();
};

function onView() {
  // 先停止动画，避免数据波动
  meta2d.stopAnimate();
  onSave(true);
  // 跳转到预览页面
  router.push({
    path: "/preview",
    query: {
      r: Date.now() + "",
      id: data._id,
    },
  });
}

function onSave(flag: boolean) {
  // 本地存储
  const data: any = meta2d.data();
  useCommonStoreWithOut().setTopology(meta2d);
  const commonStore = useCommonStore();
  console.log(commonStore.topology.store.data);
  localStorage.setItem("meta2d", JSON.stringify(data));
  if (flag) {
    message.success("保存成功");
  }
}

/**
 * 操作画布锁定
 */
function setLocked() {
  let { locked } = data.value;
  let key = 0;
  switch (locked) {
    case 0:
      key = 1;
      break;
    case 1:
      key = 2;
      break;
    case 2:
      key = 0;
      break;
  }
  data.value.locked = key; //meta2d.store.data;
  onSave(false);
}

/**
 * 增加/删除锚点
 */
const onToggleAnchorMode = () => meta2d.toggleAnchorMode();

/**
 * 添加手柄
 */
const onAddAnchorHand = () => meta2d.addAnchorHand();

/**
 * 删除手柄
 */
const onRemoveAnchorHand = () => meta2d.removeAnchorHand();

/**
 * 钢笔绘制线条
 */
function onDrawLine() {
  if (!isOnDrawLine.value) {
    // 开始绘画：curve。除了curve，还有polyline、line、mind
    meta2d.drawLine("curve");
    isOnDrawLine.value = true;
  } else {
    // 手动完成绘画
    meta2d.finishDrawLine();
    isOnDrawLine.value = false;
  }
}

/**
 * 绘制铅笔
 */
function onDrawingPencil() {
  if (!isDrawingPencil.value) {
    meta2d.drawingPencil();
    isDrawingPencil.value = true;
  } else {
    meta2d.stopPencil();
    isDrawingPencil.value = false;
  }
}

/**
 * 禁止显示锚点
 */
function onDisableAnchor() {
  if (!isDisableAnchor.value) {
    meta2d.setOptions({
      disableAnchor: true,
    });
    isDisableAnchor.value = true;
  } else {
    meta2d.setOptions({
      disableAnchor: false,
    });
    isDisableAnchor.value = false;
  }
}

/**
 * 连线时，自动选中节点锚点
 */
function onAutoAnchor() {
  if (!isAutoAnchor.value) {
    meta2d.setOptions({
      autoAnchor: true,
    });
    isAutoAnchor.value = true;
  } else {
    meta2d.setOptions({
      autoAnchor: false,
    });
    isAutoAnchor.value = false;
  }
}

/**
 * 开启或关闭放大镜
 */
function onShowMagnifier() {
  if (!isShowMagnifier.value) {
    meta2d.showMagnifier();
    isShowMagnifier.value = true;
  } else {
    meta2d.hideMagnifier();
    isShowMagnifier.value = false;
  }
}

/**
 * 打开素材库
 */
function openFileManager() {
  let fileManager = proxy.$refs.fileManager;
  fileManager.visible = true;
  nextTick(() => {
    fileManager.initMaterialFolder().then((res) => {
      fileManager.selectedKeys = [res];
      fileManager.queryParam.parent_id = res;
      fileManager.init();
    });
  });
}

/**
 * 分享
 */
function onSearch() {
  proxy.$refs.shareModal.visible = true;
}
</script>

<style lang="less" scoped>
.app-header {
  position: relative;
  width: 100%;
  height: 50px;
  padding: 0 12px;
  background: #fff;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
  border-bottom: 1px solid #dddddd;
  z-index: 3;

  .head-center {
    a {
      &.active,
      &:hover {
        color: #0c56eb;
      }
    }
  }

  .head-right {
    a {
      &:last-child {
        font-size: 18px;
      }
    }
  }

  a {
    margin: 0 8px;
    text-decoration: none;
    white-space: nowrap;
    color: #595959;

    span {
      font-size: 12px;
    }

    &:hover {
      color: #4583ff;
    }

    svg {
      margin: 0;
      font-size: 15px;
    }

    .l-icon {
      width: 1em;
      height: 1em;
      vertical-align: -0.15em;
      fill: currentColor;
      overflow: hidden;
    }
  }

  svg {
    margin: 0 8px;

    &:hover {
      color: #4583ff;
      cursor: pointer;
    }
  }
}

.ant-dropdown {
  .ant-dropdown-menu {
    .l-icon {
      width: 1em;
      height: 1em;
      vertical-align: -0.15em;
      fill: currentColor;
      overflow: hidden;
    }
  }
}
</style>