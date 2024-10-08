<template>
  <a-button type="primary" block @click="onAddEvent">增加事件</a-button>
  <div class="event-layout">
    <a-form
      ref="form"
      :data="model"
      label-align="left"
      :label-col="{ span: 10 }"
    >
      <a-collapse v-model:activeKey="activeKey" expand-icon-position="right">
        <template v-for="(vo, idx) in model" :key="idx">
          <a-collapse-panel :header="'事件 ' + (idx + 1)">
            <a-form-item label="事件类型">
              <a-select
                v-model:value="vo.name"
                allowClear
                placeholder="请选择事件类型"
                @change="changeValue(vo, 'name', idx)"
              >
                <template v-for="(item, i) in funs" :key="i">
                  <a-select-option :value="item.value">
                    {{ item.name }}
                  </a-select-option>
                </template>
              </a-select>
            </a-form-item>
            <a-form-item label="事件行为">
              <a-select
                v-model:value="vo.action"
                allowClear
                placeholder="请选择事件行为"
                @change="changeValue(vo, 'action', idx)"
              >
                <template v-for="(item, i) in eventActionList" :key="i">
                  <a-select-option :value="item.value">
                    {{ item.name }}
                  </a-select-option>
                </template>
              </a-select>
            </a-form-item>
            <template v-if="vo.action === 0">
              <a-form-item label="链接地址">
                <a-input
                  v-model:value="vo.value"
                  placeholder="请输入链接地址"
                  @blur="changeValue(vo, 'value', idx)"
                />
              </a-form-item>
              <a-form-item label="打开方式">
                <a-select
                  v-model:value="vo.params"
                  allowClear
                  placeholder="请选择打开方式"
                  @change="changeValue(vo, 'params', idx)"
                >
                  <a-select-option value="_blank">打开新窗口</a-select-option>
                  <a-select-option value="_self">覆盖当前窗口</a-select-option>
                </a-select>
              </a-form-item>
            </template>
            <template v-if="[7].includes(vo.action)">
              <a-form-item label="消息名">
                <a-select v-model:value="vo.value">
                  <a-select-option value="l-dialog">对话框</a-select-option>
                  <a-select-option value="iframe-dialog">
                    小窗展示
                  </a-select-option>
                  <a-select-option value="navigator">导航</a-select-option>
                </a-select>
              </a-form-item>
              <a-form-item label="消息参数">
                <a-input v-model:value="vo.params" />
              </a-form-item>
              <a-form-item label="全景地址">
                <a-input
                  v-model:value="vo.panoUrl"
                  placeholder="请输入全景图地址"
                />
              </a-form-item>
            </template>
            <template v-if="[8, 9, 10].includes(vo.action)">
              <a-form-item label="视频目标">
                <a-input
                  v-model:value="vo.params"
                  placeholder="请输入视频目标"
                  allowClear
                />
              </a-form-item>
            </template>
            <template v-if="[1, 11, 12].includes(vo.action)">
              <a-form-item label="目标">
                <a-input v-model:value="vo.params" placeholder="请输入目标ID" />
              </a-form-item>
              <table class="set-props-table">
                <thead>
                  <tr>
                    <td>key</td>
                    <td>value</td>
                    <td>
                      <plus-circle-outlined @click="addKeyValueNode(vo, idx)" />
                    </td>
                  </tr>
                </thead>
                <tbody>
                  <template v-for="(kv, i) in keysValue[idx].list" :key="i">
                    <tr>
                      <td>
                        <a-select
                          v-model:value="kv.key"
                          size="small"
                          style="width: 90px"
                          @change="getKV(kv, idx, i)"
                        >
                          <a-select-option value="background"
                            >背景颜色</a-select-option
                          >
                          <a-select-option value="color">背景</a-select-option>
                          <a-select-option value="text">文字</a-select-option>
                          <a-select-option value="width">宽度</a-select-option>
                          <a-select-option value="height">高度</a-select-option>
                          <a-select-option value="visible"
                            >显示</a-select-option
                          >
                          <a-select-option value="progress"
                            >进度条</a-select-option
                          >
                          <a-select-option value="value">值</a-select-option>
                          <a-select-option value="showChild"
                            >状态</a-select-option
                          >
                        </a-select>
                      </td>
                      <td>
                        <a-input
                          v-model:value="kv.value"
                          size="small"
                          style="width: 90%"
                          @change="getKV(kv, idx, i)"
                        />
                      </td>
                      <td>
                        <close-circle-outlined
                          @click="onDeleteKeyValue(i, idx)"
                        />
                      </td>
                    </tr>
                  </template>
                </tbody>
              </table>
            </template>
            <template v-if="[2, 3, 4].includes(vo.action)">
              <a-form-item label="动画目标">
                <a-input
                  v-model:value="vo.value"
                  placeholder="请输入动画目标"
                  allowClear
                />
              </a-form-item>
            </template>
            <template v-if="vo.action == 5">
              <a-form-item label="JavaScript">
                <a-button @click="openEditContainer(idx)">...</a-button>
              </a-form-item>
            </template>
            <template
              v-if="[0, 1, 2, 3, 4, 5, 7, 8, 9, 10, 11, 12].includes(vo.action)"
            >
              <a-form-item label="触发条件">
                <a-select
                  v-model:value="vo.where.type"
                  allowClear
                  placeholder="请选择触发条件"
                  @change="changeTriggerConditions(vo, idx)"
                >
                  <a-select-option :value="null">无</a-select-option>
                  <a-select-option value="comparison">关系运算</a-select-option>
                  <a-select-option value="code1">代码1</a-select-option>
                  <a-select-option value="code2">代码2</a-select-option>
                  <a-select-option value="custom"
                    >自定义代码判断</a-select-option
                  >
                </a-select>
              </a-form-item>
              <template v-if="vo.where.type == 'comparison'">
                <a-form-item label="属性名">
                  <a-input
                    v-model:value="vo.where.key"
                    placeholder="请输入属性名"
                  />
                </a-form-item>
                <a-form-item label="条件">
                  <a-select
                    v-model:value="vo.where.comparison"
                    allowClear
                    placeholder="请选择触发条件"
                    @change="changeValue(vo, 'where', idx)"
                  >
                    <a-select-option value=">">大于</a-select-option>
                    <a-select-option value=">=">大于等于</a-select-option>
                    <a-select-option value="<">小于</a-select-option>
                    <a-select-option value="<=">小于等于</a-select-option>
                    <a-select-option value="==">等于</a-select-option>
                    <a-select-option value="!=">不等于</a-select-option>
                  </a-select>
                </a-form-item>
                <a-form-item label="属性值">
                  <a-input
                    v-model:value="vo.where.value"
                    placeholder="请输入属性值"
                    @blur="onUpdateWhereParams(idx, vo.where.value)"
                  />
                </a-form-item>
              </template>
            </template>
            <template v-if="vo.where.type == 'custom'">
              <a-form-item label="高优先级判断">
                <a-button @click="onEditorEventFunc(vo.where, idx)"
                  >...</a-button
                >
              </a-form-item>
            </template>
            <template #extra>
              <delete-outlined title="删除" @click.stop="onDelete(idx)" />
            </template>
          </a-collapse-panel>
        </template>
      </a-collapse>
    </a-form>
    <EditContainer ref="editContainer" @oks="getEditTextValue" />
  </div>
</template>

<script>
import {
  ref,
  watch,
  createVNode,
  getCurrentInstance,
  nextTick,
  defineComponent,
} from "vue";
import {
  DeleteOutlined,
  PlusCircleOutlined,
  CloseCircleOutlined,
} from "@ant-design/icons-vue";
import { ExclamationCircleOutlined } from "@ant-design/icons-vue";
import { EventAction as eventAction } from "@/utils/index.ts";
import { Modal } from "ant-design-vue";
import { useSelection } from "@/services/selections";
import EditContainer from "@/components/Meta2D/EditContainer/index.vue";
import { EVENT_ACTION_TYPE, EVENT_ACTION_LIST } from "./config.ts";
export default defineComponent({
  components: {
    DeleteOutlined,
    EditContainer,
    PlusCircleOutlined,
    CloseCircleOutlined,
  },
  emits: ["event", "oks"],
  setup(props, { emit }) {
    const { selections } = useSelection();

    let { proxy } = getCurrentInstance();
    // 事件列表
    let model = ref([]);

    let index = ref(0);

    //事件类型
    let funs = ref(EVENT_ACTION_TYPE);

    // 事件行为
    let eventActionList = ref(EVENT_ACTION_LIST);

    let activeKey = ref([]);

    let keysValue = ref([]);

    function onAddEvent() {
      model.value.push({
        // 事件类型
        name: "",
        // 执行动作
        action: "",
        // 触发条件
        where: {
          type: null,
          // key: '',
          // comparison: '',
          // value: ''
        },
        value: "",
      });
      activeKey.value.push(model.value.length - 1);
      emit("event", model.value);
    }

    function init(_) {
      model.value = _;
      let list = model.value;
      list.map((_, i) => {
        activeKey.value.push(i);
        keysValue.value.push({
          list: [],
        });
        let { action, value } = _;
        switch (action) {
          case 0:
            break;
          case 1:
          case 7:
          case 8:
          case 9:
          case 10:
          case 11:
          case 12:
            let keys = Object.keys(value);
            Object.values(value).map((v, idx) => {
              keysValue.value[i].list.push({
                key: keys[idx],
                value: value[keys[idx]],
              });
            });
            break;
          default:
            break;
        }
      });
      console.log(keysValue.value, "kv.........");
    }

    function changeValue(data, key, idx) {
      switch (data.action) {
        case 0:
          break;
        case 1:
        case 7:
        case 8:
        case 9:
        case 10:
        case 11:
        case 12:
          if (
            [1, 7, 8, 9, 10, 11, 12].includes(data.action) &&
            key == "action" &&
            typeof data.value == "string"
          ) {
            keysValue.value.push({
              list: [],
            });
            model.value[idx].value = {};
          }
          break;
        case 2:
          model.value[idx].value = "";
          break;
      }
      emit("oks", model.value);
    }

    /**
     * 获取触发条件值
     */
    function changeTriggerConditions(data, idx) {
      let { type } = data.where;
      let _ = {
        type,
      };
      switch (type) {
        case "comparison":
          Object.assign(_, {
            key: "",
            comparison: "",
            value: "",
          });
          break;
        case "code1":
          Object.assign(_, {
            fnJs: "return true",
          });
          break;
        case "code2":
          Object.assign(_, {
            fnJs: "return false",
          });
          break;
        case "custom":
          Object.assign(_, {
            fnJs: "",
          });
          break;
        default:
          Object.assign(_, {
            type: null,
          });
          break;
      }
      model.value[idx].where = _;
    }

    /**
     * 删除事件
     * @param {Number} idx
     */
    function onDelete(idx) {
      Modal.confirm({
        title: "删除警告",
        icon: createVNode(ExclamationCircleOutlined),
        okText: "确定",
        cancelText: "取消",
        content: createVNode(
          "div",
          { style: "color:red;" },
          "确定删除当前事件?"
        ),
        onOk() {
          model.value.splice(idx, 1);
          activeKey.value.splice(idx, 1);
          emit("oks", model.value);
        },
      });
    }

    /**
     * 打开代码编辑器
     */
    function openEditContainer(i) {
      index.value = i;
      proxy.$refs.editContainer.visible = true;
      nextTick(() => {
        proxy.$refs.editContainer.init(model.value[i].value, "JavaScript", "");
      });
    }

    /**
     * 获取JavaScript编辑器文本信息
     */
    function onEditorEventFunc(data, i) {
      index.value = i;
      proxy.$refs.editContainer.visible = true;
      nextTick(() => {
        proxy.$refs.editContainer.init(data.fnJs, "JavaScript", "where");
      });
    }

    /**
     * 获取编辑器文本信息
     * @param {String} textValue
     */
    function getEditTextValue(textValue, type) {
      if (type !== "where") {
        model.value[index.value]["value"] = textValue;
      } else {
        Object.assign(model.value[index.value].where, {
          fnJs: textValue,
        });
      }
    }

    function addKeyValueNode(data, idx) {
      keysValue.value[idx].list.push({
        key: "",
        value: "",
      });
    }

    function getKV(param, i1, i2) {
      let lists = keysValue.value[i1].list;
      model.value[i1].value = {};
      for (let i = 0; i < lists.length; i++) {
        model.value[i1].value[lists[i].key] = lists[i].value;
      }
    }

    // 更新条件值
    function onUpdateWhereParams(index, value) {
      if (/^\d+$/.test(value)) {
        model.value[index].where.value = parseInt(value, 10);
      } else {
        model.value[index].where.value = value;
      }
    }

    /**
     * 删除keysValue数组
     */
    function onDeleteKeyValue(i, pindex) {
      keysValue.value[pindex].list.splice(i, 1);
      let lists = [];
      keysValue.value[pindex].list.map((_, i) => {
        lists.push(_.key);
      });
      let v = Object.keys(model.value[pindex].value);
      v.map((_) => {
        if (!lists.includes(_)) {
          delete model.value[pindex].value[_];
        }
      });
      emit("oks", model.value);
    }

    watch(
      () => selections.pen,
      (val) => {
        model.value = [];
        let events = val["events"];
        if (events) {
          init(events ? events : []);
        }
      }
    );

    return {
      model,
      funs,
      activeKey,
      eventActionList,
      onAddEvent,
      init,
      onDelete,
      changeValue,
      openEditContainer,
      getEditTextValue,
      changeTriggerConditions,
      addKeyValueNode,
      keysValue,
      getKV,
      onUpdateWhereParams,
      onDeleteKeyValue,
      onEditorEventFunc,
    };
  },
});
</script>

<style lang="less" scoped>
.event-layout {
  margin: 12px 0 0;
  :deep(.set-props-table) {
    width: 100%;
    margin: 0 0 12px;
    thead,
    tbody {
      tr {
        td {
          font-size: 12px;
          color: #000000d9;
          &:first-child,
          &:nth-child(2) {
            padding-left: 11px;
          }
          &:last-child {
            text-align: right;
          }
        }
      }
    }
    tbody {
      tr {
        td {
          padding: 6px 0;
        }
      }
    }
  }
  .ant-form {
    .ant-form-item {
      margin-bottom: 6px;
    }
  }
  .anticon-delete {
    &:hover {
      color: #c40000;
    }
  }
}
</style>