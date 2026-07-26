<template>
  <div class="props-panel">
    <a-tabs v-model:activeKey="tags" :tabBarStyle="tabBarStyle">
      <a-tab-pane :key="1" tab="图纸">
        <div class="mb-12">
          <a-form label-align="left" :label-col="{ span: 10 }" v-if="pen">
            <a-collapse v-model:activeKey="activeKey" size="small" expand-icon-position="right">
              <a-collapse-panel :key="1" :forceRender="true" header="位置和大小">
                <a-form-item label="X">
                  <a-input-number v-model:value="rect.x" @change="changeRect('x')" style="width: 100%" />
                </a-form-item>
                <a-form-item label="Y">
                  <a-input-number v-model:value="rect.y" @change="changeRect('y')" style="width: 100%" />
                </a-form-item>
                <a-form-item label="宽">
                  <a-input-number v-model:value="rect.width" @change="changeRect('width')" style="width: 100%" />
                </a-form-item>
                <a-form-item label="高">
                  <a-input-number v-model:value="rect.height" @change="changeRect('height')" style="width: 100%" />
                </a-form-item>
                <a-form-item label="锁定宽高比">
                  <a-switch v-model:checked="pen.ratio" @change="changeValue('ratio')" />
                </a-form-item>
                <a-form-item label="圆角">
                  <a-input-number
                    v-model:value="pen.borderRadius"
                    @change="changeValue('borderRadius')"
                    style="width: 100%"
                    placeholder="< 1 比例"
                  />
                </a-form-item>
                <a-form-item label="旋转">
                  <a-input-number v-model:value="pen.rotate" @change="changeValue('rotate')" style="width: 100%" />
                </a-form-item>
                <a-form-item label="内边距 - 上">
                  <a-input-number
                    v-model:value="pen.paddingTop"
                    @change="changeValue('paddingTop')"
                    style="width: 100%"
                  />
                </a-form-item>
                <a-form-item label="内边距 - 右">
                  <a-input-number
                    v-model:value="pen.paddingRight"
                    @change="changeValue('paddingRight')"
                    style="width: 100%"
                  />
                </a-form-item>
                <a-form-item label="内边距 - 下">
                  <a-input-number
                    v-model:value="pen.paddingBottom"
                    @change="changeValue('paddingBottom')"
                    style="width: 100%"
                  />
                </a-form-item>
                <a-form-item label="内边距 - 左">
                  <a-input-number
                    v-model:value="pen.paddingLeft"
                    @change="changeValue('paddingLeft')"
                    style="width: 100%"
                  />
                </a-form-item>
                <a-form-item label="进度">
                  <a-input-number v-model:value="pen.progress" @change="changeValue('progress')" style="width: 100%" />
                </a-form-item>
                <a-form-item label="进度颜色">
                  <ColorPicker v-model="pen.progressColor" @change="changeValue('progressColor')" />
                </a-form-item>
                <a-form-item label="垂直进度">
                  <a-switch v-model:checked="pen.verticalProgress" @change="changeValue('verticalProgress')" />
                </a-form-item>
                <a-form-item label="水平翻转">
                  <a-switch v-model:checked="pen.flipX" @change="changeValue('flipX')" />
                </a-form-item>
                <a-form-item label="垂直翻转">
                  <a-switch v-model:checked="pen.flipY" @change="changeValue('flipY')" />
                </a-form-item>
                <a-form-item label="输入框">
                  <a-switch v-model:checked="pen.input" @change="changeValue('input')" />
                </a-form-item>
                <template v-if="pen.showChild !== undefined">
                  <a-form-item label="状态">
                    <a-select v-model:value="pen.showChild" @change="changeValue('showChild')">
                      <a-select-option value="">无</a-select-option>
                      <template v-for="(vo, idx) in pen.children" :key="vo">
                        <a-select-option :value="idx"> 状态{{ idx }} </a-select-option>
                      </template>
                    </a-select>
                  </a-form-item>
                </template>
              </a-collapse-panel>
              <a-collapse-panel :key="2" :forceRender="true" header="样式">
                <a-form-item label="线条样式">
                  <a-select v-model:value="pen.dash" @change="changeValue('dash')">
                    <template v-for="(vo, idx) in configLineDash" :key="idx">
                      <a-select-option :value="idx">
                        <span v-html="vo.node"></span>
                      </a-select-option>
                    </template>
                  </a-select>
                </a-form-item>
                <a-form-item label="线条宽度">
                  <a-input-number
                    v-model:value="pen.lineWidth"
                    :step="1"
                    @change="changeValue('lineWidth')"
                    style="width: 100%"
                  />
                </a-form-item>
                <a-form-item label="边框宽度">
                  <a-input-number
                    v-model:value="pen.borderWidth"
                    @change="changeValue('borderWidth')"
                    style="width: 100%"
                  />
                </a-form-item>
                <a-form-item label="边框颜色">
                  <ColorPicker v-model="pen.borderColor" @change="changeValue('borderColor')" />
                </a-form-item>
                <a-form-item label="背景颜色">
                  <ColorPicker v-model="pen.background" @change="changeValue('background')" />
                </a-form-item>
                <a-form-item label="字体颜色">
                  <ColorPicker v-model="pen.color" @change="changeValue('color')" />
                </a-form-item>
                <a-form-item label="阴影颜色">
                  <ColorPicker v-model="pen.shadowColor" @change="changeValue('shadowColor')" />
                </a-form-item>
                <a-form-item label="边框圆角">
                  <a-input-number
                    :min="0"
                    :max="1"
                    :step="0.01"
                    v-model:value="pen.borderRadius"
                    @change="changeValue('borderRadius')"
                    style="width: 100%"
                  />
                </a-form-item>
                <a-form-item label="不透明度">
                  <a-row style="align-items: center">
                    <a-col :span="20">
                      <a-slider
                        v-model:value="pen.globalAlpha"
                        :min="0"
                        :max="1"
                        :step="0.01"
                        @change="changeValue('globalAlpha')"
                      />
                    </a-col>
                    <a-col :span="4">
                      <span class="ml-16" style="width: 50px; line-height: 30px">
                        {{ pen.globalAlpha }}
                      </span>
                    </a-col>
                  </a-row>
                </a-form-item>
              </a-collapse-panel>
              <a-collapse-panel :key="3" :forceRender="true" header="文字">
                <a-form-item label="字体名">
                  <a-input v-model:value="pen.text" @change="changeValue('text')" />
                </a-form-item>
                <a-form-item label="文字大小">
                  <a-input-number
                    v-model:value="pen.fontSize"
                    placeholder="请输入文字大小"
                    @change="changeValue('fontSize')"
                    style="width: 100%"
                  />
                </a-form-item>
                <a-form-item label="文字颜色">
                  <ColorPicker v-model="pen.textColor" @change="changeValue('textColor')" />
                </a-form-item>
                <a-form-item label="倾斜">
                  <a-select v-model:value="pen.fontStyle" @change="changeValue('fontStyle')">
                    <a-select-option value="normal">正常</a-select-option>
                    <a-select-option value="italic">倾斜</a-select-option>
                  </a-select>
                </a-form-item>
                <a-form-item label="加粗">
                  <a-select v-model:value="pen.fontWeight" @change="changeValue('fontWeight')">
                    <a-select-option value="normal">正常</a-select-option>
                    <a-select-option value="bold">加粗</a-select-option>
                  </a-select>
                </a-form-item>
                <a-form-item label="浮动文字颜色">
                  <ColorPicker v-model="pen.hoverTextColor" @change="changeValue('hoverTextColor')" />
                </a-form-item>
                <a-form-item label="背景颜色">
                  <ColorPicker v-model="pen.textBackground" @change="changeValue('textBackground')" />
                </a-form-item>
                <a-form-item label="水平对齐">
                  <a-select v-model:value="pen.textAlign" @change="changeValue('textAlign')">
                    <a-select-option value="left">左对齐</a-select-option>
                    <a-select-option value="center">居中</a-select-option>
                    <a-select-option value="right">右对齐</a-select-option>
                  </a-select>
                </a-form-item>
                <a-form-item label="垂直对齐">
                  <a-select v-model:value="pen.textBaseline" @change="changeValue('textBaseline')">
                    <a-select-option value="top">顶部对齐</a-select-option>
                    <a-select-option value="middle">居中</a-select-option>
                    <a-select-option value="bottom">底部对齐</a-select-option>
                  </a-select>
                </a-form-item>
                <a-form-item label="行高">
                  <a-input-number
                    v-model:value="pen.lineHeight"
                    @change="changeValue('lineHeight')"
                    style="width: 100%"
                  />
                </a-form-item>
                <a-form-item label="换行">
                  <a-select v-model:value="pen.whiteSpace" @change="changeValue('whiteSpace')">
                    <a-select-option value="">默认</a-select-option>
                    <a-select-option value="nowrap">不换行</a-select-option>
                    <a-select-option value="pre-line">回车换行</a-select-option>
                    <a-select-option value="break-all">永远换行</a-select-option>
                  </a-select>
                </a-form-item>
              </a-collapse-panel>
              <a-collapse-panel :key="4" :forceRender="true" header="图片">
                <a-form-item label="图片选择">
                  <div class="flex items-center">
                    <img :src="pen.image" alt="" style="width: 50px; height: 50px" />
                    <close-outlined title="清除图片" @click="clearImageField('image')" />
                  </div>
                </a-form-item>
                <a-form-item label="图片地址">
                  <div class="flex items-center" style="gap: 4px">
                    <a-input v-model:value="pen.image" placeholder="请通过右侧按钮选择图片" readonly style="flex: 1" />
                    <a-button @click="openFileManager('image')" style="flex-shrink: 0">
                      <template #icon>
                        <folder-open-outlined />
                      </template>
                    </a-button>
                  </div>
                </a-form-item>
                <a-form-item label="背景图片">
                  <div class="flex items-center">
                    <img :src="pen.backgroundImage" alt="" style="width: 50px; height: 50px" />
                    <close-outlined title="清除背景图片" @click="clearImageField('backgroundImage')" />
                  </div>
                </a-form-item>
                <a-form-item label="背景图片地址">
                  <div class="flex items-center" style="gap: 4px">
                    <a-input
                      v-model:value="pen.backgroundImage"
                      placeholder="请通过右侧按钮选择图片"
                      readonly
                      style="flex: 1"
                    />
                    <a-button @click="openFileManager('backgroundImage')" style="flex-shrink: 0">
                      <template #icon>
                        <folder-open-outlined />
                      </template>
                    </a-button>
                  </div>
                </a-form-item>
                <a-form-item label="描绘图片">
                  <div class="flex items-center">
                    <img :src="pen.strokeImage" alt="" style="width: 50px; height: 50px" />
                    <close-outlined title="清除描绘图片" @click="clearImageField('strokeImage')" />
                  </div>
                </a-form-item>
                <a-form-item label="描绘图片地址">
                  <div class="flex items-center" style="gap: 4px">
                    <a-input
                      v-model:value="pen.strokeImage"
                      placeholder="请通过右侧按钮选择图片"
                      readonly
                      style="flex: 1"
                    />
                    <a-button @click="openFileManager('strokeImage')" style="flex-shrink: 0">
                      <template #icon>
                        <folder-open-outlined />
                      </template>
                    </a-button>
                  </div>
                </a-form-item>
                <a-form-item label="宽度">
                  <a-input-number v-model:value="pen.iconWidth" placeholder="自适应" style="width: 100%" />
                </a-form-item>
                <a-form-item label="高度">
                  <a-input-number v-model:value="pen.iconHeight" placeholder="自适应" style="width: 100%" />
                </a-form-item>
                <a-form-item label="保持比例">
                  <a-switch v-model:checked="pen.imageRatio" />
                </a-form-item>
                <a-form-item label="水平偏移">
                  <a-input-number v-model:value="pen.iconLeft" placeholder="请输入水平偏移" style="width: 100%" />
                </a-form-item>
                <a-form-item label="垂直偏移">
                  <a-input-number v-model:value="pen.iconTop" placeholder="请输入垂直偏移" style="width: 100%" />
                </a-form-item>
                <a-form-item label="对齐方式">
                  <a-select v-model:value="pen.iconAlign" allowClear>
                    <a-select-option value="top">上</a-select-option>
                    <a-select-option value="right">右</a-select-option>
                    <a-select-option value="bottom">下</a-select-option>
                    <a-select-option value="left">左</a-select-option>
                    <a-select-option value="left-top">左上</a-select-option>
                    <a-select-option value="right-top">右上</a-select-option>
                    <a-select-option value="left-bottom">左下</a-select-option>
                    <a-select-option value="right-bottom">右下</a-select-option>
                    <a-select-option value="center">居中</a-select-option>
                  </a-select>
                </a-form-item>
              </a-collapse-panel>
            </a-collapse>
          </a-form>
        </div>
        <!-- <div class="mt-20">
          <a-form label-align="left" v-if="pen">
            <a-row>
              <a-col :span="12">
                <a-button block @click="top">置顶</a-button>
              </a-col>
              <a-col :span="12">
                <a-button block @click="bottom">置底</a-button>
              </a-col>
              <a-col :span="12">
                <a-button block @click="up">上一层</a-button>
              </a-col>
              <a-col :span="12">
                <a-button block @click="down">下一层</a-button>
              </a-col>
            </a-row>
          </a-form>
        </div> -->
      </a-tab-pane>
      <a-tab-pane :key="2" tab="事件">
        <EventFunc ref="eventFuncRef" @event="getEventList" @oks="getEventList" />
      </a-tab-pane>
      <a-tab-pane :key="3" tab="动效">
        <Animate ref="animateRef" :pen="pen" @onChange="changeValue" v-show="pen.name !== 'video'" />
        <VideoComputed ref="videoComputedRef" v-if="pen.name == 'video'" />
      </a-tab-pane>
      <a-tab-pane :key="4" tab="数据">
        <DataValueLayout
          ref="dataValueLayoutRef"
          @oks="onRefreshData"
          @getDataValue="getDataValue"
          @deleteDataValue="deleteDataValue"
        />
      </a-tab-pane>
    </a-tabs>
    <EditContainer ref="editContainer" @oks="getEditTextValue" />
    <!-- 弹窗 -->
    <CommonModal ref="commonModalRef" :width="'90vw'" />
    <!-- 小窗展示 -->
    <IframeModal ref="iframeModalRef" />
    <FileManager ref="fileManagerRef" :mode="'single'" @oks="onFileManagerOks" />
  </div>
</template>


<script lang="ts" setup>
// @ts-nocheck — Meta2D type definitions are too complex for strict TS checking
import { ref, watch, nextTick } from 'vue'
import { CloseOutlined, FolderOpenOutlined } from '@ant-design/icons-vue'
import { useCanvas } from '@/composables/useCanvas'
import ColorPicker from '@/components/shared/ColorPicker.vue'
import DataValueLayout from '@/components/Meta2D/DataValue/index.vue'
import CommonModal from '@/components/Meta2D/CommonModal/index.vue'
import IframeModal from '@/components/Meta2D/IframeModal/index.vue'
import EditContainer from '@/components/Meta2D/EditContainer/index.vue'
import { useSelection } from '@/services/selections'
import EventFunc from '@/components/Meta2D/Event/index.vue'
import Animate from '@/components/Meta2D/Animate/index.vue'
import VideoComputed from '@/components/Meta2D/Video/index.vue'
import { useCommonStore } from '@/store/modules/common'
import FileManager from '@/components/FileManager/index.vue'

import { CONFIG_LINE_DASH as configLineDash } from '@/utils/config-line'

const meta2d = useCanvas()

const { selections } = useSelection()

const commonStore = useCommonStore()

const tabBarStyle = ref({
  background: '#fff',
})

const activeKey = ref<number>([1, 2, 3])

const tags = ref<number>(1)

const pen = ref<any>()
// 位置数据。当前版本位置需要动态计算获取
const rect = ref<any>()

let dataIndex = -1

const fileManagerRef = ref(null)
const eventFuncRef = ref(null)
const animateRef = ref(null)
const videoComputedRef = ref(null)
const dataValueLayoutRef = ref(null)
const commonModalRef = ref(null)
const iframeModalRef = ref(null)
let currentImageField = ''

function openFileManager(field: string) {
  currentImageField = field
  const fm: any = fileManagerRef.value
  if (!fm) return
  fm.visible = true
  nextTick(() => {
    fm.initMaterialFolder().then((id: string) => {
      if (id) {
        fm.selectedKeys = [id]
        fm.queryParam.parent_id = id
      }
      fm.init()
    })
  })
}

function onFileManagerOks(params: any) {
  if (!pen.value || !currentImageField) return
  pen.value[currentImageField] = params.url
  changeValue(currentImageField)
}

function clearImageField(field: string) {
  if (!pen.value) return
  pen.value[field] = ''
  changeValue(field)
}

// Track registered meta2d event names to clean up on pen switch
const registeredHandlers: Array<{ name: string; fn: (...args: any[]) => void }> = []

function getPen() {
  pen.value = selections.pen
  if (!pen.value.globalAlpha) {
    pen.value.globalAlpha = 1
  }
  rect.value = meta2d.getPenRect(pen.value)

  // Clean up previous pen's event listeners
  registeredHandlers.forEach(({ name, fn }) => meta2d.off(name, fn))
  registeredHandlers.length = 0

  const { events } = pen.value
  if (events) {
    events.forEach((event: any) => {
      if (event.action !== 7) return
      const handler =
        event.value === 'iframe-dialog'
          ? (e: any) => {
              if (iframeModalRef.value) {
                Object.assign(iframeModalRef.value, {
                  visible: true,
                  title: '展示',
                  url: event.params,
                })
                nextTick(() => iframeModalRef.value.init(e))
              }
            }
          : (e: any) => {
              if (commonModalRef.value) {
                Object.assign(commonModalRef.value, {
                  visible: true,
                  title: '自定义弹窗',
                })
                nextTick(() => commonModalRef.value.init(event))
              }
            }
      meta2d.on(event.value, handler)
      registeredHandlers.push({ name: event.value, fn: handler })
    })
  }
}

watch(
  () => selections.pen,
  (newVal: any) => {
    if (newVal) {
      getPen()
    } else {
      registeredHandlers.forEach(({ name, fn }) => meta2d.off(name, fn))
      registeredHandlers.length = 0
    }
  },
  { immediate: true },
)

watch(
  () => tags.value,
  (tab: any) => {
    nextTick(() => {
      switch (tab) {
        case 2: {
          const data: any[] = pen.value?.events
          eventFuncRef.value?.init(data || [])
          break
        }
        case 3:
          if (pen.value?.name === 'video') {
            videoComputedRef.value?.init(pen.value)
          } else {
            animateRef.value?.init(pen.value)
          }
          break
        case 4:
          dataValueLayoutRef.value?.init(pen.value)
          break
        default:
          break
      }
    })
  },
)

let _renderTimer: ReturnType<typeof setTimeout> | null = null
function debouncedRender() {
  if (_renderTimer) clearTimeout(_renderTimer)
  _renderTimer = setTimeout(() => {
    meta2d.render()
    _renderTimer = null
  }, 100)
}

function changeValue(prop: string) {
  const v: any = { id: pen.value.id }
  v[prop] = pen.value[prop]
  if (prop === 'dash') {
    const key = v[prop]
    configLineDash.forEach((item, idx) => {
      if (key === idx) {
        v.lineDash = JSON.parse(item.value)
      }
    })
  }
  meta2d.setValue(v, { render: false })
  debouncedRender()
  commonStore.setIsSave('0')
}

function changeRect(prop: string) {
  const v: any = { id: pen.value.id }
  v[prop] = rect.value[prop]
  meta2d.setValue(v, { render: false })
  debouncedRender()
  commonStore.setIsSave('0')
}

function onRefreshData(data: any) {
  Object.assign(pen.value, {
    ...data,
  })
  commonStore.setIsSave('0')
}

function getDataValue(k: any, v: any) {
  Object.assign(pen.value, {
    [k]: v,
  })
  commonStore.setIsSave('0')
}

function deleteDataValue(k: string) {
  delete pen.value[k]
  localStorage.setItem('meta2d', JSON.stringify(meta2d.data()))
}

function getEventList(event: any) {
  pen.value.events = event
  commonStore.setIsSave('0')
}

function getEditTextValue(textValue: string) {
  pen.value.form.forEach((item: any, idx: number) => {
    if (idx === dataIndex) {
      pen.value[item.key] = textValue
    }
  })
  dataIndex = -1
  commonStore.setIsSave('0')
}
</script>

<style lang="less" scoped>
.props-panel {
  .ant-form {
    .ant-form-item {
      margin-bottom: 5px;

      img {
        margin: 0 12px 0 0;
        cursor: pointer;
      }

      .anticon-close {
        font-size: 14px;
        cursor: pointer;
      }
    }

    .a-form__label {
      padding-right: 8px;
    }

    .t-divider {
      margin: 12px 0;
    }

    :deep(.t-input--auto-width) {
      width: 100%;
    }

    .t-space {
      gap: 4px;
    }
  }
}
</style>
