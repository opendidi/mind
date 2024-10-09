<!--
 * @Descripttion:
 * @version: 1.0.0
 * @Author: htang
 * @Date: 2024-09-26 21:20:16
 * @LastEditors: htang
 * @LastEditTime: 2024-09-27 16:54:13
-->
<template>
  <a-popover v-model:visible="visible" title="素材文件上传" trigger="click">
    <template #content>
      <a-form :model="data">
        <a-form-item label="文件类型" name="type">
          <a-select v-model:value="data.type">
            <a-select-option value="image">图片</a-select-option>
            <a-select-option value="audio">音频</a-select-option>
            <a-select-option value="other">其他</a-select-option>
            <a-select-option value="panorama">全景图</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item>
          <a-upload-dragger
            v-model:fileList="fileList"
            name="file"
            :data="data"
            :multiple="true"
            :action="action"
            @change="handleChange"
          >
            <p class="ant-upload-drag-icon">
              <inbox-outlined />
            </p>
            <p class="ant-upload-hint">文件拖拽这里上传</p>
          </a-upload-dragger>
        </a-form-item>
      </a-form>
    </template>
    <a-button type="primary">上传文件</a-button>
  </a-popover>
</template>

<script lang="ts" setup>
import { ref, onMounted, getCurrentInstance, watch, nextTick } from "vue";
import { message } from "ant-design-vue";
import { InboxOutlined } from "@ant-design/icons-vue";

const emit = defineEmits(["oks"]);

let { proxy } = getCurrentInstance();

let visible = ref(false);

let data = ref({
  type: "panorama",
  parent_id: "",
});

let baseURL = import.meta.env.VITE_GLOB_API_URL;

let action = ref(baseURL + "/material/upload");

// 文件列表
let fileList = ref([]);

function handleChange(info) {
  const status = info.file.status;
  if (status == "done") {
    message.success(`${info.file.name} 文件上传成功`);
    fileList.value = [];
    visible.value = false;
    emit("oks");
  } else if (status === "error") {
    message.error(`${info.file.name} 文件上传失败。`);
  }
}

defineExpose({
  data,
});
</script>