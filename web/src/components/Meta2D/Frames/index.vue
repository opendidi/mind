<!--
 * @Descripttion:
 * @version: 1.0.0
 * @Author: htang
 * @Date: 2023-11-28 15:21:39
 * @LastEditors: htang
 * @LastEditTime: 2024-01-12 21:12:44
-->
<template>
  <a-drawer
    v-model:visible="visible"
    title="节点动画"
    placement="right"
    :width="300"
    :bodyStyle="bodyStyle"
    class="pen-frames-drawer"
  >
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
                <template v-for="field in frameFields" :key="field.key">
                  <a-form-item :label="field.label">
                    <!-- Number -->
                    <a-input-number
                      v-if="field.type === 'number'"
                      v-model:value="vo[field.key]"
                      style="width: 100%"
                      :min="field.min"
                      :max="field.max"
                    />
                    <!-- Color -->
                    <ColorPicker v-else-if="field.type === 'color'" v-model="vo[field.key]" />
                    <!-- Switch -->
                    <a-switch v-else-if="field.type === 'switch'" v-model:checked="vo[field.key]" />
                    <!-- Select -->
                    <a-select
                      v-else-if="field.type === 'select'"
                      v-model:value="vo[field.key]"
                      @change="onFrameFieldChange(field.onChange, vo[field.key], idx)"
                    >
                      <template v-for="(opt, optIdx) in getFrameSelectOptions(field.options)" :key="optIdx">
                        <a-select-option :value="field.optValue === 'idx' ? optIdx : opt[field.optValue]">
                          <span v-if="field.isHtml" v-html="opt[field.optLabel]"></span>
                          <template v-else>{{ opt[field.optLabel] }}</template>
                        </a-select-option>
                      </template>
                    </a-select>
                    <!-- Textarea -->
                    <a-textarea
                      v-else-if="field.type === 'textarea'"
                      v-model:value="vo[field.key]"
                      :auto-size="{ minRows: 2, maxRows: 5 }"
                      allow-clear
                    />
                  </a-form-item>
                </template>
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
import { ref, watch, createVNode, defineComponent } from 'vue'
import { Modal } from 'ant-design-vue'
import { DeleteOutlined, ExclamationCircleOutlined } from '@ant-design/icons-vue'
import { GRADIENT as Gradient } from '@/utils/index'
import { fontFamilys } from '@/utils/defaultConfig'
import { CONFIG_LINE_DASH as configLineDash } from '@/utils/config-line'
import ColorPicker from '@/components/shared/ColorPicker.vue'

const frameFields = [
  { label: '时长(ms)', key: 'duration', type: 'number' },
  { label: '偏移X', key: 'x', type: 'number' },
  { label: '偏移Y', key: 'y', type: 'number' },
  { label: '缩放', key: 'scale', type: 'number' },
  { label: '圆角', key: 'borderRadius', type: 'number' },
  { label: '旋转', key: 'rotate', type: 'number' },
  { label: '进度', key: 'progress', type: 'number', min: 0, max: 1 },
  { label: '进度颜色', key: 'progressColor', type: 'color' },
  { label: '水平翻转', key: 'flipX', type: 'switch' },
  { label: '垂直翻转', key: 'flipY', type: 'switch' },
  { label: '线条样式', key: 'dash', type: 'select', options: 'configLineDash', optLabel: 'node', optValue: 'idx', isHtml: true, onChange: 'changeDashValue' },
  { label: '线条宽度', key: 'lineWidth', type: 'number' },
  { label: '线条偏移', key: 'lineDashOffset', type: 'number' },
  { label: '透明度', key: 'globalAlpha', type: 'number', min: 0, max: 1 },
  { label: '显示', key: 'visible', type: 'switch' },
  { label: '线条渐变', key: 'strokeType', type: 'select', options: 'GradientList', optLabel: 'name', optValue: 'value' },
  { label: '线条渐变色', key: 'lineGradientColors', type: 'color' },
  { label: '背景', key: 'bkType', type: 'select', options: 'GradientList', optLabel: 'name', optValue: 'value' },
  { label: '背景渐变色', key: 'gradientColors', type: 'color' },
  { label: '阴影颜色', key: 'shadowColor', type: 'color' },
  { label: '阴影模糊', key: 'shadowBlur', type: 'number' },
  { label: '阴影 X 偏移', key: 'shadowOffsetX', type: 'number' },
  { label: '阴影 Y 偏移', key: 'shadowOffsetY', type: 'number' },
  { label: '文字阴影', key: 'textHasShadow', type: 'switch' },
  { label: '字体名', key: 'fontFamily', type: 'select', options: 'fontFamilys', optLabel: 'name', optValue: 'value' },
  { label: '字体大小', key: 'fontSize', type: 'number' },
  { label: '文字颜色', key: 'textColor', type: 'color' },
  { label: '浮动文字颜色', key: 'hoverTextColor', type: 'color' },
  { label: '选中文字颜色', key: 'activeTextColor', type: 'color' },
  { label: '文字报警', key: 'textBackground', type: 'color' },
  { label: '倾斜', key: 'fontStyle', type: 'select', options: 'fontStyle', optLabel: 'label', optValue: 'value' },
  { label: '加粗', key: 'fontWeight', type: 'select', options: 'fontWeight', optLabel: 'label', optValue: 'value' },
  { label: '水平对齐', key: 'textAlign', type: 'select', options: 'textAlign', optLabel: 'label', optValue: 'value' },
  { label: '垂直对齐', key: 'textBaseline', type: 'select', options: 'textBaseline', optLabel: 'label', optValue: 'value' },
  { label: '行高', key: 'lineHeight', type: 'number' },
  { label: '换行', key: 'whiteSpace', type: 'select', options: 'whiteSpace', optLabel: 'label', optValue: 'value' },
  { label: '文字宽度', key: 'textWidth', type: 'number' },
  { label: '文字高度', key: 'textHeight', type: 'number' },
  { label: '水平偏移', key: 'textLeft', type: 'number' },
  { label: '垂直偏移', key: 'textTop', type: 'number' },
  { label: '超出省略', key: 'ellipsis', type: 'select', options: 'ellipsis', optLabel: 'label', optValue: 'value' },
  { label: '文本内容', key: 'text', type: 'textarea' },
]

const staticSelectOptions = {
  fontStyle: [
    { label: '正常', value: 'normal' },
    { label: '倾斜', value: 'italic' },
  ],
  fontWeight: [
    { label: '正常', value: 'normal' },
    { label: '加粗', value: 'bold' },
  ],
  textAlign: [
    { label: '左对齐', value: 'left' },
    { label: '居中', value: 'center' },
    { label: '右对齐', value: 'right' },
  ],
  textBaseline: [
    { label: '顶部对齐', value: 'top' },
    { label: '居中', value: 'middle' },
    { label: '底部对齐', value: 'bottom' },
  ],
  whiteSpace: [
    { label: '默认', value: '' },
    { label: '不换行', value: 'nowrap' },
    { label: '回车换行', value: 'pre-line' },
    { label: '永远换行', value: 'break-all' },
  ],
  ellipsis: [
    { label: '否', value: false },
    { label: '是', value: true },
  ],
}

export default defineComponent({
  components: { DeleteOutlined, ColorPicker },
  setup(props, { emit }) {
    const visible = ref(false)
    const model = ref([])
    const animateKey = ref(0)

    function init({ frames }) {
      model.value = frames !== undefined ? frames : []
    }

    let GradientList = ref([
      { name: '没有渐变', value: Gradient.None },
      { name: '线性渐变', value: Gradient.Linear },
      { name: '发散渐变', value: Gradient.Radial },
    ])

    watch(
      () => visible.value,
      e => {
        if (!e) model.value = []
      },
    )

    function onAddFrames() {
      model.value.push({})
    }

    function changeDashValue(e, index) {
      const data = configLineDash.find((_, idx) => e == idx)
      if (data) {
        model.value[index]['lineDash'] = JSON.parse(data.value)
      }
    }

    function onDelete(idx) {
      Modal.confirm({
        title: '删除警告',
        icon: createVNode(ExclamationCircleOutlined),
        okText: '确定',
        cancelText: '取消',
        centered: true,
        content: createVNode('div', { style: 'color:red;' }, '确定删除当前动画?'),
        onOk() {
          model.value.splice(idx, 1)
        },
      })
    }

    const dynamicOptionSources = { configLineDash, GradientList, fontFamilys }

    function getFrameSelectOptions(source) {
      if (dynamicOptionSources[source]) return dynamicOptionSources[source]
      return staticSelectOptions[source] || []
    }

    function onFrameFieldChange(handler, value, index) {
      if (handler === 'changeDashValue') changeDashValue(value, index)
    }

    return {
      visible,
      model,
      animateKey,
      bodyStyle: { padding: '10px' },
      frameFields,
      fontFamilys,
      configLineDash,
      GradientList,
      onAddFrames,
      changeDashValue,
      init,
      onDelete,
      getFrameSelectOptions,
      onFrameFieldChange,
    }
  },
})
</script>

<style lang="less">
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
