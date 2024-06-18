<!--
 * @Descripttion:
 * @version: 1.0.0
 * @Author: htang
 * @Date: 2023-11-20 16:26:31
 * @LastEditors: htang
 * @LastEditTime: 2023-11-20 16:41:50
-->
<template>
  <a-modal
    v-model:visible="visible"
    :title="title"
    :width="width"
    @ok="handleOk"
    cancelText="取消"
    okText="确定"
    centered
    class="iframe-modal"
    :footer="false"
  >
    <iframe
      :src="url"
      frameborder="0"
      style="width: 100%; height: 400px"
    ></iframe>
  </a-modal>
</template>

<script>
import {
  ref,
  defineComponent,
  getCurrentInstance,
  onMounted,
  watch,
  onUnmounted,
} from "vue";
export default defineComponent({
  props: {
    width: {
      type: String,
      default: "800px",
    },
  },
  setup(props, { emit }) {
    let { proxy } = getCurrentInstance();

    let visible = ref(false);

    let title = ref("");

    let url = ref("");

    /**
     * 初始化数据
     */
    function init(params) {
      console.log(params);
    }

    /**
     *
     */
    function handleOk() {
      visible.value = false;
    }

    return {
      visible,
      title,
      handleOk,
      init,
      url,
    };
  },
});
</script>

<style lang="less" >
.iframe-modal {
  .ant-modal-body {
    padding: 0;
  }
}
</style>