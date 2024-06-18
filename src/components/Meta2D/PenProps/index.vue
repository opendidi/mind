<template>
  <div class="props-panel">
    <a-tabs v-model:activeKey="tags" :tabBarStyle="tabBarStyle">
      <a-tab-pane :key="1" tab="图纸">
        <div class="mb-12">
          <a-form label-align="left" :label-col="{ span: 10 }" v-if="pen">
            <a-collapse
              v-model:activeKey="activeKey"
              size="small"
              expand-icon-position="right"
            >
              <a-collapse-panel
                :key="1"
                :forceRender="true"
                header="位置和大小"
              >
                <a-form-item label="X">
                  <a-input-number
                    v-model:value="rect.x"
                    @change="changeRect('x')"
                    style="width: 100%"
                  />
                </a-form-item>
                <a-form-item label="Y">
                  <a-input-number
                    v-model:value="rect.y"
                    @change="changeRect('y')"
                    style="width: 100%"
                  />
                </a-form-item>
                <a-form-item label="宽">
                  <a-input-number
                    v-model:value="rect.width"
                    @change="changeRect('width')"
                    style="width: 100%"
                  />
                </a-form-item>
                <a-form-item label="高">
                  <a-input-number
                    v-model:value="rect.height"
                    @change="changeRect('height')"
                    style="width: 100%"
                  />
                </a-form-item>
                <a-form-item label="锁定宽高比">
                  <a-switch
                    v-model:checked="pen.ratio"
                    @change="changeValue('ratio')"
                  />
                </a-form-item>
                <a-form-item label="圆角">
                  <a-input-number
                    v-model:value="pen.borderRadius"
                    @change="changeValue('borderRadius')"
                    style="width: 100%"
                    placeholder="< 1 比例"
                  />
                </a-form-item>
                <a-form-item label="旋转">
                  <a-input-number
                    v-model:value="pen.rotate"
                    @change="changeValue('rotate')"
                    style="width: 100%"
                  />
                </a-form-item>
                <a-form-item label="内边距 - 上">
                  <a-input-number
                    v-model:value="pen.paddingTop"
                    @change="changeValue('paddingTop')"
                    style="width: 100%"
                  />
                </a-form-item>
                <a-form-item label="内边距 - 右">
                  <a-input-number
                    v-model:value="pen.paddingRight"
                    @change="changeValue('paddingRight')"
                    style="width: 100%"
                  />
                </a-form-item>
                <a-form-item label="内边距 - 下">
                  <a-input-number
                    v-model:value="pen.paddingBottom"
                    @change="changeValue('paddingBottom')"
                    style="width: 100%"
                  />
                </a-form-item>
                <a-form-item label="内边距 - 左">
                  <a-input-number
                    v-model:value="pen.paddingLeft"
                    @change="changeValue('paddingLeft')"
                    style="width: 100%"
                  />
                </a-form-item>
                <a-form-item label="进度">
                  <a-input-number
                    v-model:value="pen.progress"
                    @change="changeValue('progress')"
                    style="width: 100%"
                  />
                </a-form-item>
                <a-form-item label="进度颜色">
                  <t-color-picker
                    class="w-full"
                    v-model="pen.progressColor"
                    :show-primary-color-preview="false"
                    format="CSS"
                    :color-modes="['monochrome']"
                    @change="changeValue('progressColor')"
                    clearable
                  />
                </a-form-item>
                <a-form-item label="垂直进度">
                  <a-switch
                    v-model:checked="pen.verticalProgress"
                    @change="changeValue('verticalProgress')"
                  />
                </a-form-item>
                <a-form-item label="水平翻转">
                  <a-switch
                    v-model:checked="pen.flipX"
                    @change="changeValue('flipX')"
                  />
                </a-form-item>
                <a-form-item label="垂直翻转">
                  <a-switch
                    v-model:checked="pen.flipY"
                    @change="changeValue('flipY')"
                  />
                </a-form-item>
                <a-form-item label="输入框">
                  <a-switch
                    v-model:checked="pen.input"
                    @change="changeValue('input')"
                  />
                </a-form-item>
                <template v-if="pen.showChild !== undefined">
                  <a-form-item label="状态">
                    <a-select
                      v-model:value="pen.showChild"
                      @change="changeValue('showChild')"
                    >
                      <a-select-option value="">无</a-select-option>
                      <template v-for="(vo, idx) in pen.children" :key="vo">
                        <a-select-option :value="idx">
                          状态{{ idx }}
                        </a-select-option>
                      </template>
                    </a-select>
                  </a-form-item>
                </template>
              </a-collapse-panel>
              <a-collapse-panel :key="2" :forceRender="true" header="样式">
                <a-form-item label="线条样式">
                  <a-select
                    v-model:value="pen.dash"
                    @change="changeValue('dash')"
                  >
                    <template v-for="(vo, idx) in configLineDash" :key="idx">
                      <a-select-option :value="idx">
                        <span v-html="vo.node"></span>
                      </a-select-option>
                    </template>
                  </a-select>
                </a-form-item>
                <a-form-item label="线条宽度">
                  <a-input-number
                    v-model:value="pen.lineWidth"
                    :step="1"
                    @change="changeValue('lineWidth')"
                    style="width: 100%"
                  />
                </a-form-item>
                <a-form-item label="边框宽度">
                  <a-input-number
                    v-model:value="pen.borderWidth"
                    @change="changeValue('borderWidth')"
                    style="width: 100%"
                  />
                </a-form-item>
                <a-form-item label="边框颜色">
                  <t-color-picker
                    class="w-full"
                    v-model="pen.borderColor"
                    :show-primary-color-preview="false"
                    format="CSS"
                    :color-modes="['monochrome']"
                    @change="changeValue('borderColor')"
                    clearable
                  />
                </a-form-item>
                <a-form-item label="背景颜色">
                  <t-color-picker
                    class="w-full"
                    v-model="pen.background"
                    :show-primary-color-preview="false"
                    format="CSS"
                    :color-modes="['monochrome']"
                    @change="changeValue('background')"
                    clearable
                  />
                </a-form-item>
                <a-form-item label="字体颜色">
                  <t-color-picker
                    class="w-full"
                    v-model="pen.color"
                    :show-primary-color-preview="false"
                    format="CSS"
                    :color-modes="['monochrome']"
                    @change="changeValue('color')"
                    clearable
                  />
                </a-form-item>
                <a-form-item label="阴影颜色">
                  <t-color-picker
                    class="w-full"
                    v-model="pen.shadowColor"
                    :show-primary-color-preview="false"
                    format="CSS"
                    :color-modes="['monochrome']"
                    @change="changeValue('color')"
                    clearable
                  />
                </a-form-item>
                <a-form-item label="圆角">
                  <a-input-number
                    :min="0"
                    :max="1"
                    :step="0.01"
                    v-model:value="pen.borderRadius"
                    @change="changeValue('borderRadius')"
                    style="width: 100%"
                  />
                </a-form-item>
                <a-form-item label="不透明度">
                  <a-row style="align-items: center">
                    <a-col :span="20">
                      <a-slider
                        v-model:value="pen.globalAlpha"
                        :min="0"
                        :max="1"
                        :step="0.01"
                        @change="changeValue('globalAlpha')"
                      />
                    </a-col>
                    <a-col :span="4">
                      <span
                        class="ml-16"
                        style="width: 50px; line-height: 30px"
                      >
                        {{ pen.globalAlpha }}
                      </span>
                    </a-col>
                  </a-row>
                </a-form-item>
              </a-collapse-panel>
              <a-collapse-panel :key="3" :forceRender="true" header="文字">
                <a-form-item label="字体名">
                  <a-input
                    v-model:value="pen.text"
                    @change="changeValue('text')"
                  />
                </a-form-item>
                <a-form-item label="文字大小">
                  <a-input-number
                    v-model:value="pen.fontSize"
                    placeholder="请输入文字大小"
                    @change="changeValue('fontSize')"
                    style="width: 100%"
                  />
                </a-form-item>
                <a-form-item label="文字颜色">
                  <t-color-picker
                    class="w-full"
                    v-model="pen.textColor"
                    :show-primary-color-preview="false"
                    format="CSS"
                    :color-modes="['monochrome']"
                    @change="changeValue('textColor')"
                    clearable
                  />
                </a-form-item>
                <a-form-item label="倾斜">
                  <a-select
                    v-model:value="pen.fontStyle"
                    @change="changeValue('fontStyle')"
                  >
                    <a-select-option value="normal">正常</a-select-option>
                    <a-select-option value="italic">倾斜</a-select-option>
                  </a-select>
                </a-form-item>
                <a-form-item label="加粗">
                  <a-select
                    v-model:value="pen.fontWeight"
                    @change="changeValue('fontWeight')"
                  >
                    <a-select-option value="normal">正常</a-select-option>
                    <a-select-option value="bold">加粗</a-select-option>
                  </a-select>
                </a-form-item>
                <a-form-item label="浮动文字颜色">
                  <t-color-picker
                    class="w-full"
                    v-model="pen.hoverTextColor"
                    :show-primary-color-preview="false"
                    format="CSS"
                    :color-modes="['monochrome']"
                    @change="changeValue('hoverTextColor')"
                    clearable
                  />
                </a-form-item>
                <a-form-item label="背景颜色">
                  <t-color-picker
                    class="w-full"
                    v-model="pen.textBackground"
                    :show-primary-color-preview="false"
                    format="CSS"
                    :color-modes="['monochrome']"
                    @change="changeValue('textBackground')"
                    clearable
                  />
                </a-form-item>
                <a-form-item label="水平对齐">
                  <a-select
                    v-model:value="pen.textAlign"
                    @change="changeValue('textAlign')"
                  >
                    <a-select-option value="left">左对齐</a-select-option>
                    <a-select-option value="center">居中</a-select-option>
                    <a-select-option value="right">右对齐</a-select-option>
                  </a-select>
                </a-form-item>
                <a-form-item label="垂直对齐">
                  <a-select
                    v-model:value="pen.textBaseline"
                    @change="changeValue('textBaseline')"
                  >
                    <a-select-option value="top">顶部对齐</a-select-option>
                    <a-select-option value="middle">居中</a-select-option>
                    <a-select-option value="bottom">底部对齐</a-select-option>
                  </a-select>
                </a-form-item>
                <a-form-item label="行高">
                  <a-input-number
                    v-model:value="pen.lineHeight"
                    @change="changeValue('lineHeight')"
                    style="width: 100%"
                  />
                </a-form-item>
                <a-form-item label="换行">
                  <a-select
                    v-model:value="pen.whiteSpace"
                    @change="changeValue('whiteSpace')"
                  >
                    <a-select-option value="">默认</a-select-option>
                    <a-select-option value="nowrap">不换行</a-select-option>
                    <a-select-option value="pre-line">回车换行</a-select-option>
                    <a-select-option value="break-all"
                      >永远换行</a-select-option
                    >
                  </a-select>
                </a-form-item>
              </a-collapse-panel>
              <a-collapse-panel :key="4" :forceRender="true" header="图片">
                <a-form-item label="图片选择">
                  <div class="flex items-center">
                    <img
                      :src="pen.image"
                      alt=""
                      style="width: 50px; height: 50px"
                    />
                    <close-outlined title="清除图片" />
                  </div>
                </a-form-item>
                <a-form-item label="图片地址">
                  <a-input
                    v-model:value="pen.image"
                    placeholder="请输入图片地址"
                    @blur="changeValue('image')"
                  />
                </a-form-item>
                <a-form-item label="背景图片">
                  <div class="flex items-center">
                    <img
                      :src="pen.backgroundImage"
                      alt=""
                      style="width: 50px; height: 50px"
                    />
                    <close-outlined title="清除背景图片" />
                  </div>
                </a-form-item>
                <a-form-item label="背景图片">
                  <a-input
                    v-model:value="pen.backgroundImage"
                    placeholder="请输入背景图片"
                    @blur="changeValue('backgroundImage')"
                  />
                </a-form-item>
                <a-form-item label="描绘图片">
                  <div class="flex items-center">
                    <img
                      :src="pen.strokeImage"
                      alt=""
                      style="width: 50px; height: 50px"
                    />
                    <close-outlined title="清除描绘图片" />
                  </div>
                </a-form-item>
                <a-form-item label="描绘图片地址">
                  <a-input
                    v-model:value="pen.strokeImage"
                    placeholder="请输入描绘图片地址"
                    @blur="changeValue('strokeImage')"
                  />
                </a-form-item>
                <a-form-item label="宽度">
                  <a-input-number
                    v-model:value="pen.iconWidth"
                    placeholder="自适应"
                    style="width: 100%"
                  />
                </a-form-item>
                <a-form-item label="高度">
                  <a-input-number
                    v-model:value="pen.iconHeight"
                    placeholder="自适应"
                    style="width: 100%"
                  />
                </a-form-item>
                <a-form-item label="保持比例">
                  <a-switch v-model:checked="pen.imageRatio" />
                </a-form-item>
                <a-form-item label="水平偏移">
                  <a-input-number
                    v-model:value="pen.iconLeft"
                    placeholder="请输入水平偏移"
                    style="width: 100%"
                  />
                </a-form-item>
                <a-form-item label="垂直偏移">
                  <a-input-number
                    v-model:value="pen.iconTop"
                    placeholder="请输入垂直偏移"
                    style="width: 100%"
                  />
                </a-form-item>
                <a-form-item label="对齐方式">
                  <a-select v-model:value="pen.iconAlign" allowClear>
                    <a-select-option value="top">上</a-select-option>
                    <a-select-option value="right">右</a-select-option>
                    <a-select-option value="bottom">下</a-select-option>
                    <a-select-option value="left">左</a-select-option>
                    <a-select-option value="left-top">左上</a-select-option>
                    <a-select-option value="right-top">右上</a-select-option>
                    <a-select-option value="right-bottom">左下</a-select-option>
                    <a-select-option value="right-bottom">右下</a-select-option>
                    <a-select-option value="center">居中</a-select-option>
                  </a-select>
                </a-form-item>
              </a-collapse-panel>
            </a-collapse>
          </a-form>
        </div>
        <!-- <div class="mt-20">
          <a-form label-align="left" v-if="pen">
            <a-row>
              <a-col :span="12">
                <a-button block @click="top">置顶</a-button>
              </a-col>
              <a-col :span="12">
                <a-button block @click="bottom">置底</a-button>
              </a-col>
              <a-col :span="12">
                <a-button block @click="up">上一层</a-button>
              </a-col>
              <a-col :span="12">
                <a-button block @click="down">下一层</a-button>
              </a-col>
            </a-row>
          </a-form>
        </div> -->
      </a-tab-pane>
      <a-tab-pane :key="2" tab="事件">
        <EventFunc ref="eventFunc" @event="getEventList" @oks="getEventList" />
      </a-tab-pane>
      <a-tab-pane :key="3" tab="动效">
        <Animate
          ref="animate"
          :pen="pen"
          @onChange="changeValue"
          v-show="pen.name !== 'video'"
        />
        <VideoComputed ref="videoComputed" v-if="pen.name == 'video'" />
      </a-tab-pane>
      <a-tab-pane :key="4" tab="数据">
        <DataValueLayout
          ref="dataValueLayout"
          @oks="onRefreshData"
          @getDataValue="getDataValue"
          @deleteDataValue="deleteDataValue"
        />
      </a-tab-pane>
    </a-tabs>
    <EditContainer ref="editContainer" @oks="getEditTextValue" />
    <!-- 弹窗 -->
    <CommonModal ref="commonModal" :width="'90vw'" />
    <!-- 小窗展示 -->
    <IframeModal ref="iframeModal" />
  </div>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import {
  CloseOutlined,
  EditOutlined,
  DeleteOutlined,
} from "@ant-design/icons-vue";
import { Empty } from "ant-design-vue";
import DataValueLayout from "@/components/Meta2D/DataValue/index.vue";
import CommonModal from "@/components/Meta2D/CommonModal/index.vue";
import IframeModal from "@/components/Meta2D/IframeModal/index.vue";
import EditContainer from "@/components/Meta2D/EditContainer/index.vue";
import { ColorPicker } from "tdesign-vue-next";
import "tdesign-vue-next/es/style/index.css";
export default defineComponent({
  components: {
    DataValueLayout,
    CloseOutlined,
    EditOutlined,
    DeleteOutlined,
    EditContainer,
    CommonModal,
    IframeModal,
    "t-color-picker": ColorPicker,
  },
});
</script>

<script lang="ts" setup>
import {
  onMounted,
  onUnmounted,
  ref,
  watch,
  getCurrentInstance,
  nextTick,
  reactive,
} from "vue";
import { useSelection } from "@/services/selections";
import EventFunc from "@/components/Meta2D/Event/index.vue";
import Animate from "@/components/Meta2D/Animate/index.vue";
import VideoComputed from "@/components/Meta2D/Video/index.vue";

import { CONFIG_LINE_DASH as configLineDash } from "@/utils/config-line";

let { proxy } = getCurrentInstance();

const { selections } = useSelection();

let tabBarStyle = ref({
  background: "#fff",
});

let activeKey = ref<number>([1, 2, 3]);

let tags = ref<number>(1);

let simpleImage = reactive(Empty.PRESENTED_IMAGE_SIMPLE);

const pen = ref<any>();
// 位置数据。当前版本位置需要动态计算获取
const rect = ref<any>();

let dataIndex = -1;

function getPen() {
  pen.value = selections.pen;
  if (!pen.value["globalAlpha"]) {
    pen.value["globalAlpha"] = 1;
  }
  rect.value = meta2d.getPenRect(pen.value);
  let { events } = pen.value;
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
        default:
          break;
      }
    });
  }
}

// 监听选中不同图元
// @ts-ignore
const watcher = watch(() => {
  if (selections.pen) {
    selections.pen.id;
  }
}, getPen);

watch(
  () => selections.pen,
  (newVal: any) => {
    if (newVal) {
      getPen();
    }
  },
  { immediate: true }
);

watch(
  () => tags.value,
  (_: any) => {
    nextTick(() => {
      switch (_) {
        case 2:
          let data: [] = pen.value["events"];
          proxy.$refs.eventFunc.init(data ? data : []);
          break;
        case 3:
          if (pen.value.name == "video") {
            proxy.$refs.videoComputed.init(pen.value);
          } else {
            proxy.$refs.animate.init(pen.value);
          }
          break;
        case 4:
          proxy.$refs.dataValueLayout.init(pen.value);
          break;
        default:
          break;
      }
    });
  }
);

const lineDashs = [undefined, [5, 5]];

function changeValue(prop: string) {
  const v: any = { id: pen.value.id };
  v[prop] = pen.value[prop];
  switch (prop) {
    case "dash":
      let key = v[prop];
      configLineDash.map((_, idx) => {
        if (key == idx) {
          v["lineDash"] = JSON.parse(_.value);
        }
      });
      break;
    default:
      break;
  }
  meta2d.setValue(v, { render: true });
}

function changeRect(prop: string) {
  const v: any = { id: pen.value.id };
  v[prop] = rect.value[prop];
  meta2d.setValue(v, { render: true });
}

function top() {
  meta2d.top();
  meta2d.render();
}
function bottom() {
  meta2d.bottom();
  meta2d.render();
}
function up() {
  meta2d.up();
  meta2d.render();
}
function down() {
  meta2d.down();
  meta2d.render();
}

function onRefreshData(data: any) {
  Object.assign(pen.value, {
    ...data,
  });
}

function getDataValue(k: any, v: any) {
  Object.assign(pen.value, {
    [k]: v,
  });
}

function deleteDataValue(k: string) {
  delete pen.value[k];
  localStorage.setItem("meta2d", JSON.stringify(meta2d.data()));
}

function getDataDrawer(model: any) {
  if (!pen.value["form"]) {
    pen.value["form"] = [];
  }
  switch (model.type) {
    case "text":
      pen.value[model.key] = "";
      break;
    case "switch":
      pen.value[model.key] = true;
      break;
    case "number":
      pen.value[model.key] = model.min;
      break;
  }
  if (dataIndex !== -1) {
    pen.value.form.push({
      ...model,
      dataIds: {
        dataId: "",
        name: "",
      },
    });
  } else {
    Object.assign(pen.value.form[dataIndex], {
      ...model,
    });
  }
  dataIndex = -1;
}

/**
 * 编辑数据选项
 * @param {Object} data
 * @param {Number} idx
 */
function onEditData(data: any, idx: any) {
  proxy.$refs.dataDrawer.visible = true;
  dataIndex = idx;
  nextTick(() => {
    proxy.$refs.dataDrawer.init(data);
  });
}

/**
 * 获取事件列表
 * @param event 事件列表
 */
function getEventList(event: any) {
  pen.value["events"] = event;
}

/**
 * 打开代码编辑器
 */
function openEditContainer(data: any, index: number) {
  proxy.$refs.editContainer.visible = true;
  dataIndex = index;
  nextTick(() => {
    let _ = pen[data.key];
    proxy.$refs.editContainer.init(_ ? _ : "");
  });
}

/**
 * 获取编辑器文本信息
 * @param {String} textValue
 */
function getEditTextValue(textValue: string) {
  pen.value.form.map((_: any, idx: number) => {
    if (idx == dataIndex) {
      pen.value[_.key] = textValue;
    }
  });
  dataIndex = -1;
}

onMounted(() => {
  getPen();
});

onUnmounted(() => {
  watcher();
});
</script>

<style lang="less" scoped>
.props-panel {
  .ant-form {
    .ant-form-item {
      margin-bottom: 5px;
      img {
        margin: 0 12px 0 0;
        cursor: pointer;
      }
      .anticon-close {
        font-size: 14px;
        cursor: pointer;
      }
    }

    .a-form__label {
      padding-right: 8px;
    }

    .t-divider {
      margin: 12px 0;
    }

    :deep(.t-input--auto-width) {
      width: 100%;
    }

    .t-space {
      gap: 4px;
    }
  }
}
</style>