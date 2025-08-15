<!--
 * @Descripttion:
 * @version: 1.0.0
 * @Author: htang
 * @Date: 2024-09-25 12:00:26
 * @LastEditors: htang
 * @LastEditTime: 2024-09-26 21:09:32
-->
<template>
  <a-popover v-model:visible="visible" title="新建文件夹" trigger="click">
    <template #content>
      <a-form ref="formRef" :model="model" :rules="rules" layout="inline" @finish="onFinish">
        <a-form-item label="文件夹名称" name="name">
          <a-input v-model:value="model.name" placeholder="请输入文件夹名称" />
        </a-form-item>
        <a-form-item>
          <a-button type="primary" html-type="submit">提交保存</a-button>
        </a-form-item>
      </a-form>
    </template>
    <a-button type="primary">
      <icon name="folder-add" class="mr-1" />
      <span>创建文件夹</span>
    </a-button>
  </a-popover>
</template>

<script setup>
import { ref, onMounted, getCurrentInstance, watch } from "vue";
import { apiMaterialCreatedFolder } from "@/api/material";
import { Icon } from "tdesign-vue-next";

let visible = ref(false);
let { proxy } = getCurrentInstance();

const emit = defineEmits(["oks"]);

let model = ref({
  name: "",
  parent_id: "",
});

let rules = ref({
  name: [{ required: true, message: "请输入文件夹名称" }],
});

function onFinish(values) {
  let data = {};
  let keys = Object.keys(model.value);
  Object.values(model.value).map((_, i) => {
    if (_ !== "") {
      data[keys[i]] = _;
    }
  });
  apiMaterialCreatedFolder({ ...data }).then((res) => {
    visible.value = false;
    proxy.$refs.formRef.resetFields();
    emit("oks");
  });
}

defineExpose({
  model,
});
</script>