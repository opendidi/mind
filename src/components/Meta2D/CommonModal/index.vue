<!--
 * @Descripttion:
 * @version: 1.0.0
 * @Author: htang
 * @Date: 2023-10-11 20:04:32
 * @LastEditors: htang
 * @LastEditTime: 2024-04-10 16:23:41
-->
<template>
  <a-modal
    v-model:visible="visible"
    :title="title"
    :width="width"
    @ok="handleOk"
    :destroyOnClose="true"
    wrapClassName="message-common-modal"
    :maskClosable="false"
    cancelText="取消"
    okText="确定"
    centered
  >
    <div id="pano"></div>
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
      default: "520px",
    },
  },
  setup(props, { emit }) {
    let { proxy } = getCurrentInstance();

    let visible = ref(false);

    let title = ref("");

    /**
     * 初始化数据
     */
    function init(params) {
      let { panoUrl } = params;
      if (panoUrl) {
        let root = panoUrl.split("/").slice(0, 4).join("/");
        embedpano({
          swf: `${root}/pano/tour.swf`,
          xml: params.panoUrl,
          target: "pano",
          html5: "prefer",
          mobilescale: 1.0,
          passQueryParameters: true,
        });
      }
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
    };
  },
});
</script>

<style lang="less" scoped>
.message-common-modal {
  background: red;
  .ant-modal-body {
    padding: 12px;
  }
  #pano {
    width: 100%;
    height: calc(100vh - 300px);
  }
}
</style>