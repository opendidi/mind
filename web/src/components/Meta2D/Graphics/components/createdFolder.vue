<!--
 * @Descripttion:
 * @version: 1.0.0
 * @Author: htang
 * @Date: 2024-09-25 12:00:26
 * @LastEditors: htang
 * @LastEditTime: 2025-08-18 19:52:58
-->
<template>
  <a-modal
    v-model:visible="visible"
    centered
    width="30%"
    :destroyOnClose="true"
    cancelText="取消"
    okText="确定"
    title="新建文件夹"
    @ok="onFinish"
    @cancel="visible = false"
  >
    <a-form ref="formRef" :model="model" :rules="rules">
      <a-form-item label="文件夹名称" name="name">
        <a-input v-model:value="model.name" placeholder="请输入文件夹名称" />
      </a-form-item>
    </a-form>
  </a-modal>
</template>

<script setup>
import { ref, onMounted, getCurrentInstance, watch } from "vue";
import { Icon } from "tdesign-vue-next";

const visible = ref(false);

const { proxy } = getCurrentInstance();

const emit = defineEmits(["oks"]);

const formRef = ref(null);

const model = ref({
  name: "",
  parent_id: "",
});

const rules = ref({
  name: [{ required: true, message: "请输入文件夹名称" }],
});

watch(
  () => visible.value,
  (val) => {
    if (!val) {
      formRef.value.resetFields();
    }
  }
);

function onFinish(values) {
  formRef.value.validate().then(() => {
    let data = {};
    let keys = Object.keys(model.value);
    Object.values(model.value).map((_, i) => {
      if (_ !== "") {
        data[keys[i]] = _;
      }
    });
    visible.value = false;
  });
}

defineExpose({
  visible,
});
</script>