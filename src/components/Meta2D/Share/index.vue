<!--
 * @Descripttion:
 * @version: 1.0.0
 * @Author: htang
 * @Date: 2023-10-11 11:15:10
 * @LastEditors: htang
 * @LastEditTime: 2024-10-08 19:57:08
-->
<template>
  <a-modal
    v-model:visible="visible"
    title="分享此项目"
    centered
    :footer="false"
    :destroyOnClose="true"
  >
    <div class="qrcode-layer">
      <a-form ref="form" :model="model">
        <a-form-item>
          <a-input-group compact>
            <a-input
              v-model:value="model.url"
              style="width: calc(100% - 88px)"
              readOnly
            />
            <a-button type="primary" @click="onCopy">复制链接</a-button>
          </a-input-group>
        </a-form-item>
      </a-form>
      <a-row>
        <a-col>
          <a-card
            :bodyStyle="{
              width: 120,
            }"
            size="small"
            :bordered="false"
          >
            <template #cover>
              <qrcode-vue
                :value="model.url"
                :size="120"
                level="H"
                style="margin: 0 auto"
              />
            </template>
            <a-card-meta>
              <template #description>
                <span style="text-align: center; display: inherit">扫一扫</span>
              </template>
            </a-card-meta>
          </a-card>
        </a-col>
      </a-row>
    </div>
  </a-modal>
</template>

<script>
import { ref, defineComponent, getCurrentInstance, nextTick } from "vue";
import useClipboard from "vue-clipboard3";
import { message } from "ant-design-vue";
import QrcodeVue from "qrcode.vue";
export default defineComponent({
  components: { QrcodeVue },
  setup() {
    let { proxy } = getCurrentInstance();

    let visible = ref(false);

    const { toClipboard } = useClipboard();

    let date = Date.now();
    let args = [`id=${proxy.$route.query.id || 1}`, `r=${date + ""}`];
    let model = ref({
      url: `${window.location.href}/metaPreview?${args.join("&")}`,
    });

    async function onCopy() {
      await toClipboard(model.value.url);
      message.success("复制链接成功!");
    }

    return {
      visible,
      model,
      onCopy,
    };
  },
});
</script>