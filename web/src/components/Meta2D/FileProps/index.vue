<template>
  <div class="props-panel">
    <a-tabs v-model:activeKey="tags" :tabBarStyle="tabBarStyle">
      <a-tab-pane :key="1" tab="图纸">
        <div class="mb-12">
          <a-collapse v-model:activeKey="fileKey" size="small" expand-icon-position="right">
            <a-collapse-panel :key="1" :forceRender="true" header="文件">
              <a-form label-align="left" :label-col="{ span: 7 }">
                <a-form-item label="文件名称">
                  <a-input v-model:value="data.name" @change="onChangeData('name', data.name)" />
                </a-form-item>
              </a-form>
            </a-collapse-panel>
            <a-collapse-panel :key="2" :forceRender="true" header="画布">
              <a-form label-align="left" :label-col="{ span: 10 }">
                <a-form-item label="默认颜色">
                  <t-color-picker
                    class="w-full"
                    v-model="options.color"
                    :show-primary-color-preview="false"
                    format="CSS"
                    :color-modes="['monochrome']"
                    @change="onChangeOptions('color', options.color)"
                    clearable
                  />
                </a-form-item>
                <a-form-item label="画笔填充颜色">
                  <t-color-picker
                    class="w-full"
                    v-model="data.penBackground"
                    :show-primary-color-preview="false"
                    format="CSS"
                    :color-modes="['monochrome']"
                    @change="onChangeData('penBackground', data.penBackground)"
                    clearable
                  />
                </a-form-item>
                <a-form-item label="背景颜色" name="background">
                  <t-color-picker
                    class="w-full"
                    v-model="data.background"
                    :show-primary-color-preview="false"
                    format="CSS"
                    :color-modes="['monochrome']"
                    @change="onChangeData('background', data.background)"
                    clearable
                  />
                </a-form-item>
                <a-form-item label="背景网格">
                  <a-switch v-model:checked="options.grid" @change="onChangeData('grid', options.grid)" />
                </a-form-item>
                <a-form-item label="网格颜色">
                  <t-color-picker
                    class="w-full"
                    v-model="options.gridColor"
                    :show-primary-color-preview="false"
                    format="CSS"
                    :color-modes="['monochrome']"
                    @change="onChangeData('gridColor', options.gridColor)"
                    clearable
                  />
                </a-form-item>
                <a-form-item label="网格大小">
                  <a-input-number
                    v-model:value="options.gridSize"
                    @change="onChangeData('gridSize', options.gridSize)"
                    style="width: 100%"
                    :min="0"
                  />
                </a-form-item>
                <a-form-item label="网格角度">
                  <a-input-number
                    v-model:value="options.gridRotate"
                    @change="onChangeData('gridRotate', options.gridRotate)"
                    style="width: 100%"
                    :min="0"
                  />
                </a-form-item>
                <a-form-item label="标尺">
                  <a-switch v-model:checked="options.rule" @change="onChangeData('rule', options.rule)" />
                </a-form-item>
                <a-form-item label="标尺颜色">
                  <t-color-picker
                    class="w-full"
                    v-model="options.ruleColor"
                    :show-primary-color-preview="false"
                    format="CSS"
                    :color-modes="['monochrome']"
                    @change="onChangeData('ruleColor', options.ruleColor)"
                    clearable
                  />
                </a-form-item>
                <a-form-item label="初始化JS">
                  <a-button @click="openEditContainer">...</a-button>
                </a-form-item>
              </a-form>
            </a-collapse-panel>
          </a-collapse>
        </div>
      </a-tab-pane>
      <a-tab-pane :key="2" tab="通信">
        <div class="mb-12">
          <a-collapse v-model:activeKey="activeKey" size="small" expand-icon-position="right">
            <a-collapse-panel :key="1" :forceRender="true" header="WebSocket">
              <a-input v-model:value="data.websocket" placeholder="请输入websocket地址" @blur="getWebSocketData" />
            </a-collapse-panel>
            <a-collapse-panel :key="2" :forceRender="true" header="MQTT">
              <a-form :model="mqttForm" :rules="mqttRules" label-align="left" :label-col="{ span: 10 }" @finish="onMqttDataFinish">
                <a-form-item label="URL地址" name="mqtt">
                  <a-input v-model:value="mqttForm.mqtt" />
                </a-form-item>
                <a-form-item label="Client ID">
                  <a-input v-model:value="mqttForm.mqttOptions.clientId" />
                </a-form-item>
                <a-form-item label="关闭自动生成">
                  <a-switch v-model:checked="mqttForm.mqttOptions.customClientId" />
                </a-form-item>
                <a-form-item label="用户名">
                  <a-input v-model:value="mqttForm.mqttOptions.username" />
                </a-form-item>
                <a-form-item label="密码">
                  <a-input v-model:value="mqttForm.mqttOptions.password" />
                </a-form-item>
                <a-form-item label="Topics" name="mqttTopics">
                  <a-input v-model:value="mqttForm.mqttTopics" placeholder="多个topic以英文逗号“,”分隔" />
                </a-form-item>
                <a-form-item label="操作">
                  <a-button type="primary" html-type="submit" style="width: 100%">提交</a-button>
                </a-form-item>
              </a-form>
            </a-collapse-panel>
            <a-collapse-panel :key="3" :forceRender="true" header="HTTP通信">
              <a-form label-align="left" :label-col="{ span: 7 }">
                <template v-for="(vo, idx) in https" :key="idx">
                  <a-card :title="'http' + (idx + 1)" size="small" style="width: 100%`" :bordered="false">
                    <template #extra>
                      <template v-if="idx !== 0">
                        <a @click="onDeleteHttpNode(vo, idx)">删除</a>
                      </template>
                    </template>
                    <a-form-item label="URL地址" name="gridSize" @change="setHttpData(vo, idx)">
                      <a-input v-model:value="vo.http" @blur="onChangeOptions" style="width: 100%" />
                    </a-form-item>
                    <a-form-item label="请求方式" name="name">
                      <a-select v-model:value="vo.method" placeholder="默认GET" auto-width clearable @change="setHttpData(vo, idx)">
                        <a-select-option value="GET">GET</a-select-option>
                        <a-select-option value="POST">POST</a-select-option>
                      </a-select>
                    </a-form-item>
                    <a-form-item label="时间间隔">
                      <a-input-number v-model:value="vo.httpTimeInterval" @blur="setHttpData(vo, idx)" style="width: 100%" />
                    </a-form-item>
                    <a-form-item label="请求头">
                      <a-button @click="openEditContainerSettingHeader(vo, idx)">...</a-button>
                    </a-form-item>
                  </a-card>
                </template>
                <a-button block @click="onAddHttpSetData">
                  <template #icon>
                    <plus-outlined />
                  </template>
                  增加HTTP通信
                </a-button>
              </a-form>
            </a-collapse-panel>
            <a-collapse-panel :key="4" :forceRender="true" header="消息处理JavaScript">
              <a-form label-align="left" :label-col="{ span: 8 }">
                <a-form-item label="消息处理">
                  <a-button @click="onOpenEditContainerSocketCbJs">...</a-button>
                </a-form-item>
              </a-form>
            </a-collapse-panel>
          </a-collapse>
        </div>
      </a-tab-pane>
      <a-tab-pane :key="3" tab="布局">
        <div class="mb-12"></div>
      </a-tab-pane>
    </a-tabs>
    <EditContainer ref="editContainer" :title="editContainerTitle" @oks="getEditTextValue" @close="closeEditContainer" />
  </div>
</template>

<script lang="ts">
import { defineComponent } from 'vue';
import { ColorPicker } from 'tdesign-vue-next';
import 'tdesign-vue-next/es/style/index.css';
export default defineComponent({
  components: {
    't-color-picker': ColorPicker,
  },
});
</script>

<script lang="ts" setup>
import { onMounted, ref, nextTick, watch, reactive, getCurrentInstance } from 'vue';
import { PlusOutlined, DeleteOutlined } from '@ant-design/icons-vue';
import { message } from 'ant-design-vue';
import EditContainer from '@/components/Meta2D/EditContainer/index.vue';
import { useCommonStore, useCommonStoreWithOut } from '@/store/modules/common';

let { proxy } = getCurrentInstance();

const commonStore = useCommonStore();

let tags = ref<number>(1);
let fileKey = ref<number>([1, 2, 3, 4]);
let activeKey = ref<number>([1, 2, 3]);

// 图纸数据
const data = reactive<any>({
  name: '',
  background: undefined,
  color: undefined,
});

let tabBarStyle = reactive({
  background: '#fff',
});

let mqttForm = reactive({
  // mqtt地址
  mqtt: '',
  // mqtt 订阅主题
  mqttTopics: '',
  mqttOptions: {
    // 客户端ID
    clientId: '',
    // 用户名
    username: '',
    // 密码
    password: '',
    // ture - clientId不变；false - clientId随机，避免相同连接clientId冲突
    customClientId: false,
  },
});

let mqttRules = reactive({
  mqtt: [{ required: true, message: '请输入MQTT地址' }],
  mqttTopics: [{ required: true, message: '请输入Topics' }],
});

let https = ref([
  {
    http: '',
    method: '',
    // 轮询间隔时间
    httpTimeInterval: 1000,
    // 请求头设置
    httpHeaders: {},
  },
]);
let httpsIndex = 0;

let isOpenSocketEditContainer = false;

// 画布选项
const options = reactive<{
  grid: boolean;
  gridSize: number;
  gridRotate: undefined;
  gridColor: undefined;
  rule: boolean;
}>({
  grid: false,
  gridSize: 10,
  gridRotate: undefined,
  gridColor: undefined,
  rule: true,
});

let editContainerTitle = ref<string>();

/**
 * 初始化数据
 */
function onInit(dataValue) {
  const d: any = dataValue; //JSON.parse(useCommonStore().originalData);

  if (d['https']) {
    if (d['https'].length !== 0) {
      meta2d.store.data.https = d['https'];
      meta2d.connectHttp();
      https.value = d['https'];
    }
  } else {
    meta2d.store.data.https = https.value;
    meta2d.connectHttp();
  }

  if (d['websocket'] == '') {
    data['websocket'] = '';
    meta2d.store.data['websocket'] = '';
  }

  Object.assign(data, {
    name: d.name || '',
    background: d.background,
    color: d.color,
    ...d,
  });

  Object.assign(options, meta2d.getOptions());
}

onMounted(() => {
  // const d: any = meta2d.data();
  // meta2d.socketFn = (message, context) => {
  //   let info = JSON.parse(message);
  //   let dataList = JSON.parse(info.data);
  //   console.log(dataList);
  //   // let pens = [];
  //   dataList.map((item) => {
  //     item['id'] = item['dot'];
  //     if (item['vtype'] === 'FLOAT') {
  //       item['text'] = parseFloat(item['value']).toFixed(2);
  //     } else {
  //       item['text'] = item['value'];
  //     }
  //     meta2d.setValue({
  //       ...item,
  //     });
  //   });
  //   // Do sth
  //   // return false; //表示仅执行自定义的回调函数方法
  //   return true; //表示除了执行自定义的回调方法外，还会执行核心库方法
  // };
  // meta2d.setValue({ dataId: "device-001", value: 20 });
});

function onChangeData(key: string, dataValue: string) {
  switch (key) {
    case 'background':
      meta2d.setBackgroundColor(dataValue);
      break;
    case 'grid':
    case 'gridColor':
    case 'gridSize':
    case 'gridRotate':
      meta2d.setGrid({ [key]: dataValue });
      break;
    case 'rule':
    case 'ruleColor':
      meta2d.setRule({ [key]: dataValue });
      break;
    default:
      break;
  }
  meta2d.store.data[key] = dataValue;
  // meta2d.store.patchFlagsBackground = true;
  meta2d.render();
}

/**
 * 获取socket地址
 */
function getWebSocketData() {
  const pattern = /^wss?:\/\/[^\s/$.?#].[^\s]*$/i;
  let url = data['websocket'];
  if (url) {
    if (pattern.test(url)) {
      meta2d.store.data['websocket'] = url;
    } else {
      nextTick(() => {
        message.warning('不符合 WebSocket 地址的格式');
      });
    }
  } else if (url == '') {
    meta2d.store.data['websocket'] = '';
  }
}

function onChangeOptions() {
  meta2d.setOptions(options);
  meta2d.render();
}

function setHttpData(data: any, idx: any) {
  if (data) {
    meta2d.store.data.https = https.value;
    meta2d.connectHttp();
  }
}

function onAddHttpSetData() {
  https.value.push({
    http: '',
    method: '',
    // 轮询间隔时间
    httpTimeInterval: 3000,
    // 请求头设置
    httpHeaders: {},
  });
}

/**
 * 打开代码编辑器
 */
function openEditContainer() {
  proxy.$refs.editContainer.visible = true;
  editContainerTitle.value = 'JavaScript';
  nextTick(() => {
    let _ = meta2d.store.data['initJs'];
    proxy.$refs.editContainer.init(_ ? _ : '');
  });
}

/**
 * 打开编辑器编辑HTTP请求头配置信息
 */
function openEditContainerSettingHeader(data: any, idx: number) {
  proxy.$refs.editContainer.visible = true;
  httpsIndex = idx;
  nextTick(() => {
    editContainerTitle.value = '请求头配置';
    proxy.$refs.editContainer.init(JSON.stringify(data.httpHeaders), 'json');
  });
}

/**
 * 当编辑器关闭后状态还原
 */
function closeEditContainer() {
  editContainerTitle.value = '';
  isOpenSocketEditContainer = false;
}

/**
 * 打开编辑器编辑消息处理JavaScript
 */
function onOpenEditContainerSocketCbJs() {
  proxy.$refs.editContainer.visible = true;
  isOpenSocketEditContainer = true;
  nextTick(() => {
    let _ = meta2d.store.data['socketCbJs'];
    editContainerTitle.value = 'JavaScript';
    proxy.$refs.editContainer.init(_ ? _ : '');
  });
}

/**
 * 获取编辑器文本信息
 * @param {String} textValue
 */
function getEditTextValue(textValue: string) {
  if (editContainerTitle.value.indexOf('请求头配置') !== -1) {
    https[httpsIndex].httpHeaders = JSON.parse(textValue);
    meta2d.store.data.https = https.value;
    editContainerTitle.value = '';
  } else if (isOpenSocketEditContainer == true) {
    meta2d.store.data['socketCbJs'] = textValue;
    isOpenSocketEditContainer = false;
  } else {
    meta2d.store.data['initJs'] = textValue;
  }
}

function onDeleteHttpNode(data: any, idx: number) {
  https.value.splice(idx, 1);
}

/**
 * https://doc.le5le.com/document/119620524#MQTT
 */
function onMqttDataFinish() {
  // 连接新配置
  meta2d.connectMqtt(mqttForm);
}

defineExpose({
  onInit,
});

// setTimeout(() => {
//   // websocket
//   meta2d.websocket.send('[{dataId: 43,value: 1}]');
// }, 6000);
</script>

<style lang="less" scoped>
.props-panel {
  height: 100%;
  background: #fff;
  .ant-tabs {
    .ant-divider {
      // margin: 6px 0;
    }
    :deep .ant-collapse-item {
      border-bottom: 1px solid #d9d9d9;
      box-sizing: border-box;
      .ant-collapse-header {
        // padding: 6px 0;
      }
    }
    :deep .ant-collapse-content-box {
      padding: 6px;
    }
    .ant-form {
      .ant-form-item {
        margin-bottom: 6px;
        :deep(.t-input--auto-width) {
          width: 100% !important;
        }
        .anticon {
          margin: 0 0 0 12px;
          font-size: 24px;
          cursor: pointer;
          &:hover {
            color: var(--color-error);
          }
        }
        &:last-child {
          margin-bottom: 0;
        }
      }
    }
  }
}
</style>