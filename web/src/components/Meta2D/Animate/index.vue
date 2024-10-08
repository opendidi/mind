<!--
 * @Descripttion:
 * @version: 1.0.0
 * @Author: htang
 * @Date: 2023-09-14 08:57:16
 * @LastEditors: htang
 * @LastEditTime: 2024-04-03 10:25:32
-->
<template>
  <a-form
    label-align="left"
    :label-col="{ span: 10 }"
    v-if="model"
    class="animate-form"
  >
    <a-collapse
      v-model:activeKey="animateKey"
      size="small"
      expand-icon-position="right"
    >
      <a-collapse-panel :key="1" header="动画">
        <template v-if="model.name !== 'line'">
          <a-form-item label="时长">
            <a-input
              v-model:value="model.duration"
              readOnly
              :bordered="false"
              style="width: 100%"
            />
          </a-form-item>
        </template>
        <a-form-item label="动画效果">
          <template v-if="model.name == 'line'">
            <a-select
              v-model:value="model.lineAnimateType"
              @change="changeValue('lineAnimateType')"
              placeholder="请选择动画效果"
            >
              <a-select-option :value="0">水流</a-select-option>
              <a-select-option :value="1">水珠流动</a-select-option>
              <a-select-option :value="2">圆点</a-select-option>
            </a-select>
          </template>
          <template v-else>
            <a-select
              v-model:value="model.animateType"
              @change="changeAnimate"
              placeholder="请选择动画效果"
            >
              <a-select-option value="">无</a-select-option>
              <template v-for="vo in animateType" :key="vo.key">
                <a-select-option :value="vo.key">
                  {{ vo.name }}
                </a-select-option>
              </template>
            </a-select>
            <template v-if="model.animateType == 'custom'">
              <a-button size="small" class="mt-12" @click="openFrames"
                >编辑</a-button
              >
            </template>
          </template>
        </a-form-item>
        <a-form-item label="循环次数">
          <a-input-number
            v-model:value="model.animateCycle"
            @change="changeValue('animateCycle')"
            style="width: 100%"
          />
        </a-form-item>
        <a-form-item label="下个动画">
          <a-input
            v-model:value="model.nextAnimate"
            @change="changeValue('nextAnimate')"
            placeholder="tag"
          />
        </a-form-item>
        <a-form-item label="自动播放">
          <a-switch
            v-model:checked="model.autoPlay"
            @change="changeValue('autoPlay')"
          />
        </a-form-item>
        <a-form-item label="保持动画状态">
          <a-switch
            v-model:checked="model.keepAnimateState"
            @change="changeValue('keepAnimateState')"
          />
        </a-form-item>
        <a-form-item label="动画线宽">
          <a-input-number
            v-model:value="model.animateLineWidth"
            @change="changeValue('animateLineWidth')"
            style="width: 100%"
            placeholder="请输入动画线宽"
          />
        </a-form-item>
        <a-form-item label="动画颜色">
          <t-color-picker
            class="w-full"
            v-model="model.animateColor"
            :show-primary-color-preview="false"
            format="CSS"
            :color-modes="['monochrome']"
            @change="changeValue('animateColor')"
            clearable
          />
        </a-form-item>
        <a-form-item label="动画速度">
          <a-slider
            v-model:value="model.animateSpan"
            :show-tooltip="true"
            :min="1"
            :max="5"
            @change="changeValue('animateSpan')"
          />
        </a-form-item>
        <a-form-item label="反向流动">
          <a-switch
            v-model:checked="model.animateReverse"
            @change="changeValue('animateReverse')"
          />
        </a-form-item>
        <a-form-item label="线性播放">
          <a-select v-model:value="model.linear">
            <a-select-option :value="true">是</a-select-option>
            <a-select-option :value="false">否</a-select-option>
          </a-select>
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
    <FramesDrawer ref="framesDrawer" />
  </a-form>
</template>

<script>
import { ref, watch, defineComponent, getCurrentInstance, nextTick } from "vue";
import {
  CaretRightOutlined,
  PauseOutlined,
  CloseOutlined,
} from "@ant-design/icons-vue";
import { animateType } from "@/utils/defaultConfig.ts";
import { useSelection } from "@/services/selections";
import FramesDrawer from "@/components/Meta2D/Frames/index.vue";
import { ColorPicker } from "tdesign-vue-next";
import "tdesign-vue-next/es/style/index.css";
export default defineComponent({
  components: {
    CaretRightOutlined,
    PauseOutlined,
    CloseOutlined,
    FramesDrawer,
    "t-color-picker": ColorPicker,
  },
  emits: ["onChange"],
  setup(props, { emit }) {
    const { selections } = useSelection();
    let { proxy } = getCurrentInstance();
    let model = ref({
      autoPlay: false,
      frames: [],
      duration: 0,
      animateCycle: Infinity,
    });

    let animateKey = 1;

    function init(_) {
      model.value = _;
    }

    function changeValue(prop) {
      emit("onChange", prop);
    }

    /**
     * 选择动画
     */
    function changeAnimate(f) {
      const data = animateType.find((_) => _.key == f);
      if (data) {
        let { frames } = data;
        if (frames.length !== 0) {
          Object.assign(model.value, {
            frames,
            duration: frames[0].duration,
          });
        }
        Object.keys(model.value).map((_) => {
          if (["animateType", "frames"].includes(_)) {
            changeValue(_);
          }
        });
      }
    }

    /**
     * 开始播放动画
     */
    function onPlay() {
      meta2d.startAnimate(model.value.id);
    }

    /**
     * 暂停播放
     */
    function onPause() {
      meta2d.pauseAnimate(model.value.id);
    }

    /**
     * 结束动画
     */
    function onStop() {
      meta2d.stopAnimate(model.value.id);
    }

    /**
     * 打开编辑动画帧弹窗
     */
    function openFrames() {
      proxy.$refs.framesDrawer.visible = true;
      nextTick(() => {
        proxy.$refs.framesDrawer.init(model.value);
      });
    }

    watch(
      () => model.value.animateType,
      (e) => {
        const data = animateType.find((_) => _.key == e);
        if (data) {
          model.value["frames"] = data.frames;
        }
      }
    );

    watch(
      () => selections.pen,
      (val) => {
        init(val);
      }
    );

    return {
      changeValue,
      animateType,
      model,
      animateKey,
      init,
      onPlay,
      onPause,
      onStop,
      openFrames,
      changeAnimate,
    };
  },
});
</script>
<style lang="less" scoped>
.animate-form {
  .ant-form-item {
    margin-bottom: 6px;
  }
}
</style>