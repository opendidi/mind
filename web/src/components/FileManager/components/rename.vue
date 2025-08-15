<!--
 * @Descripttion:
 * @version: 1.0.0
 * @Author: htang
 * @Date: 2025-05-26 18:03:07
 * @LastEditors: htang
 * @LastEditTime: 2025-06-18 18:12:03
-->
<template>
  <a-modal
    v-model:visible="visible"
    title="修改文件标题名称"
    centered
    @ok="onFinish"
  >
    <a-form ref="formRef" :model="model" :rules="rules">
      <a-form-item label="文件名" name="name">
        <a-input v-model:value="model.name" />
      </a-form-item>
    </a-form>
  </a-modal>
</template>

<script setup>
import { ref } from "vue";
import { apiMaterialModify } from "@/api/material";

const visible = ref(false);

const emit = defineEmits(["oks"]);

const formRef = ref(null);

const model = ref({
  name: "",
});

const rules = {
  name: [
    {
      required: true,
      message: "请输入文件名",
    },
  ],
};

const init = (params) => {
  Object.assign(model.value, { ...params });
};

const onFinish = async () => {
  try {
    const validate = await formRef.value.validate();
    let data = {
      ...model.value,
    };
    apiMaterialModify(data).then((res) => {
      visible.value = false;
      emit("success", model.value);
      formRef.value.resetFields();
    });
  } catch (error) {
    console.log("验证失败:", error);
  }
};

defineExpose({
  visible,
  init,
});
</script>