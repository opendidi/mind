<!--
 * @Descripttion:
 * @version: 1.0.0
 * @Author: htang
 * @Date: 2023-09-11 08:50:37
 * @LastEditors: htang
 * @LastEditTime: 2023-09-19 16:13:57
-->
<template>
  <a-drawer
    v-model:visible="visible"
    title="表单提交"
    placement="right"
    class="drawer-form-data"
    :drawerStyle="drawerStyle"
    :bodyStyle="bodyStyle"
    :width="400"
    @afterVisibleChange="onAfterVisibleChange"
  >
    <a-form
      ref="form"
      :model="model"
      :rules="rules"
      label-align="left"
      :label-col="{ span: 6 }"
      @finish="onFinish"
    >
      <a-form-item label="显示名称" name="name">
        <a-input v-model:value="model.name" placeholder="请输入名称" />
      </a-form-item>
      <a-form-item label="属性名" name="key">
        <a-input v-model:value="model.key" placeholder="请输入属性" />
      </a-form-item>
      <a-form-item label="类型" name="type">
        <a-select v-model:value="model.type" placeholder="请选择类型">
          <a-select-option value="text">文本</a-select-option>
          <a-select-option value="number">数字</a-select-option>
          <a-select-option value="color">颜色</a-select-option>
          <a-select-option value="textarea">多行文本</a-select-option>
          <a-select-option value="select">下拉框</a-select-option>
          <a-select-option value="switch">开关</a-select-option>
          <a-select-option value="code">Json</a-select-option>
          <a-select-option value="slider">滑块</a-select-option>
        </a-select>
      </a-form-item>
      <template
        v-if="
          [
            'text',
            'number',
            'color',
            'textarea',
            'switch',
            'code',
            'slider',
          ].includes(model.type)
        "
      >
        <a-form-item label="提示文字" name="placeholder">
          <a-input v-model:value="model.placeholder" />
        </a-form-item>
      </template>
      <template v-if="model.type == 'select'">
        <template v-for="(vo, idx) in model.options" :key="idx">
          <a-form-item label="选项名">
            <a-input v-model:value="vo.label" placeholder="请输入选项名" />
          </a-form-item>
          <a-form-item label="选项值">
            <div class="flex items-center justify-between">
              <a-input v-model:value="vo.value" placeholder="请输入选项值" />
              <delete-outlined title="删除" @click="onDelete(idx)" />
            </div>
          </a-form-item>
        </template>
        <a-form-item label="-">
          <a-button type="primary" @click="addOptions">
            <template #icon>
              <plus-outlined />
            </template>
            新增选项
          </a-button>
        </a-form-item>
      </template>
      <template v-if="['number', 'slider'].includes(model.type)">
        <a-form-item label="最小值">
          <a-input-number v-model:value="model.min" />
        </a-form-item>
        <a-form-item label="最大值">
          <a-input-number v-model:value="model.max" />
        </a-form-item>
        <a-form-item label="步长">
          <a-input-number v-model:value="model.step" />
        </a-form-item>
        <a-form-item label="精度">
          <a-input-number v-model:value="model.precision" />
        </a-form-item>
      </template>
      <a-form-item label="操作">
        <a-button type="primary" html-type="submit">确定</a-button>
      </a-form-item>
    </a-form>
  </a-drawer>
</template>

<script>
import { ref, watch, getCurrentInstance, defineComponent } from "vue";
import { DeleteOutlined, PlusOutlined } from "@ant-design/icons-vue";
export default defineComponent({
  components: { DeleteOutlined, PlusOutlined },
  setup(props, { emit }) {
    let { proxy } = getCurrentInstance();
    let visible = ref(false);
    let model = ref({
      // 名称
      name: "",
      // 属性
      key: "",
      // 类型
      type: "",
      // 描述
      placeholder: "",
    });
    let rules = ref({});

    let drawerStyle = ref({});

    let bodyStyle = ref({
      padding: "12px",
    });

    watch(
      () => model.value.type,
      (type) => {
        if (type !== "select") {
          delete model.value.options;
        }
        if (!["number", "slider"].includes(type)) {
          delete model.value.min;
          delete model.value.max;
          delete model.value.step;
          delete model.value.precision;
        }
      }
    );

    const addOptions = () => {
      if (model.value["options"] == undefined) {
        model.value["options"] = [];
      }
      model.value["options"].push({
        label: "",
        value: "",
      });
    };

    const init = (data) => {
      model.value = data;
      console.log(data);
    };

    const onDelete = (idx) => {
      model.value.options.splice(idx, 1);
    };

    const onFinish = () => {
      emit("oks", model.value);
      visible.value = false;
      proxy.$refs.form.resetFields();
    };

    const onAfterVisibleChange = (e) => {
      if (!e) {
        proxy.$refs.form.resetFields();
      }
    };

    return {
      visible,
      model,
      rules,
      drawerStyle,
      bodyStyle,
      init,
      addOptions,
      onDelete,
      onFinish,
      onAfterVisibleChange,
    };
  },
});
</script>

<style lang="less" scoped>
.drawer-form-data {
  .ant-form {
    .ant-form-item {
      margin-bottom: 14px;
      .ant-input-number,
      .ant-button {
        width: 100%;
      }
      .anticon-delete {
        margin: 0 0 0 12px;
        font-size: 26px;
        cursor: pointer;
        &:hover {
          color: red;
        }
      }
    }
  }
}
</style>