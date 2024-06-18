<template>
  <a-modal
    v-model:visible="visible"
    wrapClassName="dialog-select-form"
    title="编辑下拉列表"
    okText="确定"
    cancelText="取消"
    @ok="handleOk"
  >
    <a-form :model="model" :rules="rules">
      <a-form-item label="选项名" name="text">
        <a-input v-model:value="model.text" placeholder="请输入选项名" />
      </a-form-item>
      <a-form-item label="选项值">
        <a-tooltip placement="top">
          <template #title>
            <span
              >选项值，即选择该选项后同时修改的内容，例如：background: #f40,
              表示的意思是，选择该项后，画笔的背景颜色变成 #f40</span
            >
          </template>
          <question-circle-outlined />
        </a-tooltip>
      </a-form-item>
      <a-form-item>
        <table class="set-props-table">
          <thead>
            <tr>
              <td>key</td>
              <td>value</td>
              <td>
                <plus-circle-outlined
                  title="新增"
                  @click="addKeyValueNode(vo, idx)"
                />
              </td>
            </tr>
          </thead>
          <tbody>
            <template v-for="(kv, i) in model.keysValue" :key="i">
              <tr>
                <td>
                  <a-select
                    v-model:value="kv.key"
                    style="width: 100%"
                    allowClear
                  >
                    <a-select-option value="background">
                      背景颜色
                    </a-select-option>
                    <a-select-option value="color">背景</a-select-option>
                    <a-select-option value="width">宽度</a-select-option>
                    <a-select-option value="height">高度</a-select-option>
                    <a-select-option value="visible">显示</a-select-option>
                    <a-select-option value="progress">进度值</a-select-option>
                    <a-select-option value="value">值</a-select-option>
                  </a-select>
                </td>
                <td>
                  <a-input
                    v-model:value="kv.value"
                    style="width: 100%"
                    allowClear
                  />
                </td>
                <td>
                  <close-circle-outlined
                    title="删除"
                    @click="onDeleteKeyValue(i)"
                  />
                </td>
              </tr>
            </template>
          </tbody>
        </table>
      </a-form-item>
    </a-form>
  </a-modal>
</template>

<script>
import { ref, watch, getCurrentInstance, defineComponent } from "vue";
import {
  QuestionCircleOutlined,
  PlusCircleOutlined,
  CloseCircleOutlined,
} from "@ant-design/icons-vue";
export default defineComponent({
  components: {
    QuestionCircleOutlined,
    PlusCircleOutlined,
    CloseCircleOutlined,
  },
  setup(props, { emit }) {
    let visible = ref(false);

    let idx = ref();

    let model = ref({
      text: "",
      keysValue: [],
    });

    let rules = ref({
      text: [{ required: true, message: "请输入选项名" }],
    });

    watch(
      () => visible.value,
      (bool) => {
        if (!bool) {
          model.value = {
            text: "",
            keysValue: [],
          };
          idx.value = "";
        }
      }
    );

    /**
     * 初始化数据
     */
    const init = (_, i) => {
      idx.value = i;
      let { text } = _;
      Object.assign(model.value, {
        text,
        keysValue: [],
      });
      let keys = Object.keys(_);
      Object.values(_).map((_, idx) => {
        if (keys[idx] !== "text") {
          model.value.keysValue.push({
            key: keys[idx],
            value: _,
          });
        }
      });
    };

    const addKeyValueNode = (data, idx) => {
      model.value.keysValue.push({
        key: "",
        value: "",
      });
    };

    /**
     * 删除keysValue数组
     */
    const onDeleteKeyValue = (i) => {
      model.value.keysValue.splice(i, 1);
    };

    const handleOk = () => {
      let { text, keysValue } = model.value;
      let data = {
        text,
      };
      keysValue.map((_, i) => {
        Object.assign(data, {
          [_.key]: _.value,
        });
      });
      visible.value = false;
      emit("oks", data, idx.value);
      idx.value = "";
    };

    return {
      visible,
      model,
      rules,
      idx,
      init,
      addKeyValueNode,
      onDeleteKeyValue,
      handleOk,
    };
  },
});
</script>

<style lang="less" scoped>
.dialog-select-form {
  .ant-form {
    .ant-form-item {
      &:last-child {
        margin-bottom: 0;
      }
    }
  }
  .set-props-table {
    width: 100%;
    thead,
    tbody {
      tr {
        td {
          font-size: 12px;
          color: #000000d9;
          &:first-child,
          &:nth-child(2) {
            padding-right: 11px;
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
}
</style>