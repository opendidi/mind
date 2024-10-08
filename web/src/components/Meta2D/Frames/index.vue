<!--
 * @Descripttion:
 * @version: 1.0.0
 * @Author: htang
 * @Date: 2023-11-28 15:21:39
 * @LastEditors: htang
 * @LastEditTime: 2024-01-12 21:12:44
-->
<template>
  <a-drawer v-model:visible="visible" title="节点动画" placement="right" :width="300" :bodyStyle="bodyStyle" class="pen-frames-drawer">
    <a-button type="primary" style="width: 100%" @click="onAddFrames">新增动画帧</a-button>
    <template v-if="model.length !== 0">
      <div class="mt-4">
        <a-form ref="form" :data="model" label-align="left" :label-col="{ span: 10 }">
          <a-collapse v-model:activeKey="animateKey" size="small" expand-icon-position="right">
            <template v-for="(vo, idx) in model" :key="idx">
              <a-collapse-panel>
                <template #header>
                  <span>
                    {{ '动画帧 ' + (idx + 1) + '/' + model.length }}
                  </span>
                </template>
                <a-form-item label="时长(ms)">
                  <a-input-number v-model:value="vo.duration" style="width: 100%" />
                </a-form-item>
                <a-form-item label="偏移X">
                  <a-input-number v-model:value="vo.x" style="width: 100%" />
                </a-form-item>
                <a-form-item label="偏移Y">
                  <a-input-number v-model:value="vo.y" style="width: 100%" />
                </a-form-item>
                <a-form-item label="缩放">
                  <a-input-number v-model:value="vo.scale" style="width: 100%" />
                </a-form-item>
                <a-form-item label="圆角">
                  <a-input-number v-model:value="vo.borderRadius" style="width: 100%" />
                </a-form-item>
                <a-form-item label="旋转">
                  <a-input-number v-model:value="vo.rotate" style="width: 100%" />
                </a-form-item>
                <a-form-item label="进度">
                  <a-input-number v-model:value="vo.progress" style="width: 100%" :max="1" :min="0" />
                </a-form-item>
                <a-form-item label="进度颜色">
                  <t-color-picker
                    class="w-full"
                    v-model="vo.progressColor"
                    :show-primary-color-preview="false"
                    format="CSS"
                    :color-modes="['monochrome']"
                    clearable
                  />
                </a-form-item>
                <a-form-item label="水平翻转">
                  <a-switch v-model:checked="vo.flipX" />
                </a-form-item>
                <a-form-item label="垂直翻转">
                  <a-switch v-model:checked="vo.flipY" />
                </a-form-item>
                <a-form-item label="线条样式">
                  <a-select v-model:value="vo.dash" @change="changeDashValue(vo.dash, idx)">
                    <template v-for="(vo, idx) in configLineDash" :key="idx">
                      <a-select-option :value="idx">
                        <span v-html="vo.node"></span>
                      </a-select-option>
                    </template>
                  </a-select>
                </a-form-item>
                <a-form-item label="线条宽度">
                  <a-input-number v-model:value="vo.lineWidth" style="width: 100%" />
                </a-form-item>
                <a-form-item label="线条偏移">
                  <a-input-number v-model:value="vo.lineDashOffset" style="width: 100%" />
                </a-form-item>
                <a-form-item label="透明度">
                  <a-input-number v-model:value="vo.globalAlpha" style="width: 100%" :max="1" :min="0" />
                </a-form-item>
                <a-form-item label="显示">
                  <a-switch v-model:checked="vo.visible" />
                </a-form-item>
                <a-form-item label="线条渐变">
                  <a-select v-model:value="vo.strokeType">
                    <template v-for="(vo, idx) in GradientList" :key="idx">
                      <a-select-option :value="vo.value">
                        {{ vo.name }}
                      </a-select-option>
                    </template>
                  </a-select>
                </a-form-item>
                <a-form-item label="线条渐变色">
                  <t-color-picker
                    class="w-full"
                    v-model="vo.lineGradientColors"
                    :show-primary-color-preview="false"
                    format="CSS"
                    :color-modes="['monochrome']"
                    clearable
                  />
                </a-form-item>
                <a-form-item label="背景">
                  <a-select v-model:value="vo.bkType">
                    <template v-for="(vo, idx) in GradientList" :key="idx">
                      <a-select-option :value="vo.value">
                        {{ vo.name }}
                      </a-select-option>
                    </template>
                  </a-select>
                </a-form-item>
                <a-form-item label="背景渐变色">
                  <t-color-picker
                    class="w-full"
                    v-model="vo.gradientColors"
                    :show-primary-color-preview="false"
                    format="CSS"
                    :color-modes="['monochrome']"
                    clearable
                  />
                </a-form-item>
                <a-form-item label="阴影颜色">
                  <t-color-picker
                    class="w-full"
                    v-model="vo.shadowColor"
                    :show-primary-color-preview="false"
                    format="CSS"
                    :color-modes="['monochrome']"
                    clearable
                  />
                </a-form-item>
                <a-form-item label="阴影模糊">
                  <a-input-number v-model="vo.shadowBlur" style="width: 100%" />
                </a-form-item>
                <a-form-item label="阴影 X 偏移">
                  <a-input-number v-model="vo.shadowOffsetX" style="width: 100%" />
                </a-form-item>
                <a-form-item label="阴影 Y 偏移">
                  <a-input-number v-model="vo.shadowOffsetY" style="width: 100%" />
                </a-form-item>
                <a-form-item label="文字阴影">
                  <a-switch v-model:checked="vo.textHasShadow" />
                </a-form-item>
                <a-form-item label="字体名">
                  <a-select v-model:value="vo.fontFamily">
                    <template v-for="(vo, idx) in fontFamilys" :key="idx">
                      <a-select-option :value="vo.value">
                        {{ vo.name }}
                      </a-select-option>
                    </template>
                  </a-select>
                </a-form-item>
                <a-form-item label="字体大小">
                  <a-input-number v-model="vo.fontSize" style="width: 100%" />
                </a-form-item>
                <a-form-item label="文字颜色">
                  <t-color-picker
                    class="w-full"
                    v-model="vo.textColor"
                    :show-primary-color-preview="false"
                    format="CSS"
                    :color-modes="['monochrome']"
                    clearable
                  />
                </a-form-item>
                <a-form-item label="浮动文字颜色">
                  <t-color-picker
                    class="w-full"
                    v-model="vo.hoverTextColor"
                    :show-primary-color-preview="false"
                    format="CSS"
                    :color-modes="['monochrome']"
                    clearable
                  />
                </a-form-item>
                <a-form-item label="选中文字颜色">
                  <t-color-picker
                    class="w-full"
                    v-model="vo.activeTextColor"
                    :show-primary-color-preview="false"
                    format="CSS"
                    :color-modes="['monochrome']"
                    clearable
                  />
                </a-form-item>
                <a-form-item label="文字报警">
                  <t-color-picker
                    class="w-full"
                    v-model="vo.textBackground"
                    :show-primary-color-preview="false"
                    format="CSS"
                    :color-modes="['monochrome']"
                    clearable
                  />
                </a-form-item>
                <a-form-item label="倾斜">
                  <a-select v-model:value="vo.fontStyle">
                    <a-select-option value="normal">正常</a-select-option>
                    <a-select-option value="italic">倾斜</a-select-option>
                  </a-select>
                </a-form-item>
                <a-form-item label="加粗">
                  <a-select v-model:value="vo.fontWeight">
                    <a-select-option value="normal">正常</a-select-option>
                    <a-select-option value="bold">加粗</a-select-option>
                  </a-select>
                </a-form-item>
                <a-form-item label="浮动文字颜色">
                  <t-color-picker
                    class="w-full"
                    v-model="vo.hoverTextColor"
                    :show-primary-color-preview="false"
                    format="CSS"
                    :color-modes="['monochrome']"
                    clearable
                  />
                </a-form-item>
                <a-form-item label="背景颜色">
                  <t-color-picker
                    class="w-full"
                    v-model="vo.textBackground"
                    :show-primary-color-preview="false"
                    format="CSS"
                    :color-modes="['monochrome']"
                    clearable
                  />
                </a-form-item>
                <a-form-item label="水平对齐">
                  <a-select v-model:value="vo.textAlign">
                    <a-select-option value="left">左对齐</a-select-option>
                    <a-select-option value="center">居中</a-select-option>
                    <a-select-option value="right">右对齐</a-select-option>
                  </a-select>
                </a-form-item>
                <a-form-item label="垂直对齐">
                  <a-select v-model:value="vo.textBaseline">
                    <a-select-option value="top">顶部对齐</a-select-option>
                    <a-select-option value="middle">居中</a-select-option>
                    <a-select-option value="bottom">底部对齐</a-select-option>
                  </a-select>
                </a-form-item>
                <a-form-item label="行高">
                  <a-input-number v-model:value="vo.lineHeight" style="width: 100%" />
                </a-form-item>
                <a-form-item label="换行">
                  <a-select v-model:value="vo.whiteSpace">
                    <a-select-option value="">默认</a-select-option>
                    <a-select-option value="nowrap">不换行</a-select-option>
                    <a-select-option value="pre-line">回车换行</a-select-option>
                    <a-select-option value="break-all">永远换行</a-select-option>
                  </a-select>
                </a-form-item>
                <a-form-item label="文字宽度">
                  <a-input-number v-model:value="vo.textWidth" style="width: 100%" />
                </a-form-item>
                <a-form-item label="文字高度">
                  <a-input-number v-model:value="vo.textHeight" style="width: 100%" />
                </a-form-item>
                <a-form-item label="水平偏移">
                  <a-input-number v-model:value="vo.textLeft" style="width: 100%" />
                </a-form-item>
                <a-form-item label="垂直偏移">
                  <a-input-number v-model:value="vo.textTop" style="width: 100%" />
                </a-form-item>
                <a-form-item label="超出省略">
                  <a-select v-model:value="vo.ellipsis">
                    <a-select-option :value="false">否</a-select-option>
                    <a-select-option :value="true">是</a-select-option>
                  </a-select>
                </a-form-item>
                <a-form-item label="文本内容">
                  <a-textarea v-model:value="vo.text" :auto-size="{ minRows: 2, maxRows: 5 }" allow-clear />
                </a-form-item>
                <template #extra>
                  <delete-outlined title="删除" @click.stop="onDelete(idx)" />
                </template>
              </a-collapse-panel>
            </template>
          </a-collapse>
        </a-form>
      </div>
    </template>
  </a-drawer>
</template>

<script>
import { ref, reactive, watch, createVNode, onMounted, defineComponent, getCurrentInstance } from 'vue';
import { Modal } from 'ant-design-vue';
import { DeleteOutlined, ExclamationCircleOutlined } from '@ant-design/icons-vue';
import { GRADIENT as Gradient } from '@/utils/index';
import { fontFamilys } from '@/utils/defaultConfig';
import { CONFIG_LINE_DASH as configLineDash } from '@/utils/config-line';
export default defineComponent({
  components: { DeleteOutlined },
  setup(props, { emit }) {
    let { proxy } = getCurrentInstance();

    let visible = ref(false);

    let model = ref([]);

    let animateKey = ref(0);

    /**
     * 初始化动画帧
     */
    function init({ frames }) {
      model.value = frames !== undefined ? frames : [];
    }

    let GradientList = ref([
      {
        name: '没有渐变',
        value: Gradient.None,
      },
      {
        name: '线性渐变',
        value: Gradient.Linear,
      },
      {
        name: '发散渐变',
        value: Gradient.Radial,
      },
    ]);

    watch(
      () => visible.value,
      (e) => {
        if (!e) {
          model.value = [];
        }
      }
    );

    /**
     * 增加帧动画文本节点
     */
    function onAddFrames() {
      model.value.push({});
    }

    /**
     * 选择线条样式
     */
    function changeDashValue(e, index) {
      const data = configLineDash.find((_, idx) => e == idx);
      if (data) {
        model.value[index]['lineDash'] = JSON.parse(data.value);
      }
    }

    /**
     * 删除动画
     */
    function onDelete(idx) {
      Modal.confirm({
        title: '删除警告',
        icon: createVNode(ExclamationCircleOutlined),
        okText: '确定',
        cancelText: '取消',
        centered: true,
        content: createVNode('div', { style: 'color:red;' }, '确定删除当前动画?'),
        onOk() {
          model.value.splice(idx, 1);
        },
      });
    }

    return {
      visible,
      model,
      animateKey,
      bodyStyle: {
        padding: `10px`,
      },
      fontFamilys,
      onAddFrames,
      configLineDash,
      changeDashValue,
      init,
      GradientList,
      onDelete,
    };
  },
});
</script>

<style lang="less" >
.pen-frames-drawer {
  .ant-form {
    .ant-form-item {
      margin-bottom: 12px;
    }
    .t-input--auto-width {
      width: 100%;
    }
  }
}
</style>