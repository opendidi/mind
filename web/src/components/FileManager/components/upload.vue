<!--
 * @Descripttion:
 * @version: 1.0.0
 * @Author: htang
 * @Date: 2024-09-26 21:20:16
 * @LastEditors: htang
 * @LastEditTime: 2025-08-15 11:22:22
-->
<template>
  <template v-if="data.parent_id !== ''">
    <a-upload v-model:fileList="fileList" name="file" :data="data" :accept="accept" :multiple="true" :action="action" :showUploadList="false" @change="handleChange" :before-upload="beforeUpload">
      <a-button type="primary" class="ant-upload-hint w-full">
        上传文件
      </a-button>
    </a-upload>
  </template>
  <template v-else>
    <a-button type="primary" :disabled="true" style="width: 95%">
      上传文件
    </a-button>
  </template>
</template>

<script lang="ts" setup>
import {
  ref,
  getCurrentInstance,
  computed,
} from "vue";
import { message } from "ant-design-vue";
import { FileExplorer } from "@/utils/FileExplorer.ts";

const emit = defineEmits(["oks"]);

const api_url = import.meta.env.VITE_GLOB_API_URL;

const { proxy }: any = getCurrentInstance();

const visible = ref(false);

const file_type = ref("");

const accept = computed(() => {
  switch (file_type.value) {
    case "image":
    case "panorama":
      return new FileExplorer()._filterExt.image.join(",");
    case "video":
      return new FileExplorer()._filterExt.video.join(",");
    case "audio":
      return new FileExplorer()._filterExt.audio.join(",");
    default:
      break;
  }
});

let data = ref({
  type: file_type.value ? file_type.value : "panorama",
  parent_id: "",
});

let action = computed(() => {
  return api_url + "material/upload";
});

// 文件列表
let fileList = ref([]);

const beforeUpload = (file: any) => {
  console.log(file);
};

function handleChange(info: any) {
  const status = info.file.status;
  if (status == "done") {
    if (info.file.response.code == 200) {
      message.success(`${info.file.name} 文件上传成功`);
      fileList.value = [];
      visible.value = false;
    } else {
      message.error(`文件上传失败。`);
    }
    emit("oks");
  } else if (status === "error") {
    message.error(`${info.file.name} 文件上传失败。`);
  }
}

defineExpose({
  data,
  file_type,
});
</script>