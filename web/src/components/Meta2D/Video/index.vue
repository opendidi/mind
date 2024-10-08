<!--
 * @Descripttion:
 * @version: 1.0.0
 * @Author: htang
 * @Date: 2024-04-10 10:59:01
 * @LastEditors: htang
 * @LastEditTime: 2024-04-10 11:54:39
-->
<template>
  <a-form
    label-align="left"
    :label-col="{ span: 10 }"
    v-if="model"
    class="video-form"
  >
    <a-collapse
      v-model:activeKey="animateKey"
      size="small"
      expand-icon-position="right"
    >
      <a-collapse-panel :key="1" header="视频">
        <a-form-item label="音频URL">
          <a-input
            v-model:value="model.audio"
            :bordered="false"
            style="width: 100%"
          />
        </a-form-item>
        <a-form-item label="视频URL">
          <a-input
            v-model:value="model.video"
            :bordered="false"
            style="width: 100%"
          />
        </a-form-item>
        <a-form-item label="自动播放">
          <a-switch
            v-model:checked="model.autoPlay"
            @change="changeValue('autoPlay')"
          />
        </a-form-item>
        <a-form-item label="下个播放">
          <a-input
            v-model:value="model.nextAnimate"
            :bordered="false"
            style="width: 100%"
          />
        </a-form-item>
        <a-form-item label="循环播放">
          <a-switch
            v-model:checked="model.playLoop"
            @change="changeValue('playLoop')"
          />
        </a-form-item>
        <a-form-item>
          <div class="flex items-center justify-between">
            <a-button type="primary" @click="onPlay()">
              <template #icon>
                <caret-right-outlined />
              </template>
              <span>播放</span>
            </a-button>
            <a-button type="dashed" @click="onPause()">
              <template #icon>
                <pause-outlined />
              </template>
              <span>暂停</span>
            </a-button>
            <a-button danger @click="onStop()">
              <template #icon>
                <close-outlined />
              </template>
              <span>停止</span>
            </a-button>
          </div>
        </a-form-item>
      </a-collapse-panel>
    </a-collapse>
  </a-form>
</template>

<script>
import { ref, watch, defineComponent, getCurrentInstance, nextTick } from "vue";
import {
  CaretRightOutlined,
  PauseOutlined,
  CloseOutlined,
} from "@ant-design/icons-vue";
export default defineComponent({
  components: {
    CaretRightOutlined,
    PauseOutlined,
    CloseOutlined,
  },
  setup(props, { emit }) {
    let { proxy } = getCurrentInstance();

    let animateKey = 1;

    let model = ref({
      // 音频
      audio: "",
      // 视频地址
      video: "",
      // 下一个tab
      nextAnimate: "",
    });

    function init(_) {
      model.value = {
        ..._,
      };
    }

    function changeValue(prop) {
      emit("onChange", prop);
    }

    /**
     * 开始播放动画
     */
    function onPlay() {
      meta2d.startVideo(model.value.id);
    }

    /**
     * 暂停播放
     */
    function onPause() {
      meta2d.pauseVideo(model.value.id);
    }

    /**
     * 结束动画
     */
    function onStop() {
      meta2d.stopVideo(model.value.id);
    }

    return {
      init,
      model,
      animateKey,
      changeValue,
      onPlay,
      onPause,
      onStop,
    };
  },
});
</script>

<style lang="less" scoped>
.video-form {
  .ant-form-item {
    margin-bottom: 6px;
  }
}
</style>