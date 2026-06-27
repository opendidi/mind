<template>
  <div class="app-header flex items-center justify-between">
    <div class="head-left flex items-center">
      <a-dropdown>
        <a class="ant-dropdown-link flex items-center flex-col">
          <div class="flex items-center">
            <t-icon name="folder" />
            <t-icon name="chevron-down-s" />
          </div>
          <span>文件</span>
        </a>
        <template #overlay>
          <a-menu>
            <a-menu-item divider="true">
              <a class="flex items-center" @click="createBluePrint">
                <t-icon name="numbers-1-1" />
                <span>新建图纸</span>
              </a>
            </a-menu-item>
            <a-menu-item>
              <a class="flex items-center" @click="downloadJson">
                <t-icon name="numbers-2" />
                <span>下载JSON文件</span>
              </a>
            </a-menu-item>
            <a-menu-item>
              <a class="flex items-center" @click="downloadPng">
                <t-icon name="numbers-3" />
                <span>下载为PNG</span>
              </a>
            </a-menu-item>
            <a-menu-item>
              <a class="flex items-center" @click="downloadSvg">
                <t-icon name="numbers-4" />
                <span>下载为SVG</span>
              </a>
            </a-menu-item>
          </a-menu>
        </template>
      </a-dropdown>
      <a-dropdown>
        <a class="ant-dropdown-link flex items-center flex-col">
          <div class="flex items-center">
            <t-icon name="edit-1" />
            <t-icon name="chevron-down-s" />
          </div>
          <span>编辑</span>
        </a>
        <template #overlay>
          <a-menu>
            <a-menu-item>
              <a @click="onToggleAnchorMode">
                <div class="flex items-center">
                  <t-icon name="numbers-1-1" />
                  <span>增加/删除锚点</span>
                </div>
              </a>
            </a-menu-item>
            <a-menu-item>
              <a @click="onAddAnchorHand">
                <div class="flex items-center">
                  <t-icon name="numbers-2" />
                  <span>添加手柄</span>
                </div>
              </a>
            </a-menu-item>
            <a-menu-item>
              <a @click="onRemoveAnchorHand">
                <div class="flex items-center">
                  <t-icon name="numbers-3" />
                  <span>删除手柄</span>
                </div>
              </a>
            </a-menu-item>
          </a-menu>
        </template>
      </a-dropdown>
      <a-badge :dot="dot">
        <a class="flex items-center flex-col" @click="onSave(true)">
          <t-icon name="save" />
          <span>保存</span>
        </a>
      </a-badge>
    </div>
    <div class="head-center flex items-center">
      <a class="flex items-center flex-col" :class="[isOnDrawLine == true ? 'active' : '']" @click="onDrawLine">
        <t-icon name="pen" />
        <span>钢笔</span>
      </a>
      <a class="flex items-center flex-col" :class="[isDrawingPencil == true ? 'active' : '']" @click="onDrawingPencil">
        <t-icon name="edit" />
        <span>铅笔</span>
      </a>
      <a class="flex items-center flex-col" :class="[isShowMagnifier == true ? 'active' : '']" @click="onShowMagnifier">
        <t-icon name="search" />
        <span>放大镜</span>
      </a>
      <a class="flex items-center flex-col" :class="[visibleMap == true ? 'active' : '']" @click="onOpenMap()">
        <t-icon name="location" />
        <span>鹰眼地图</span>
      </a>
      <a class="flex items-center flex-col" @click="onUndo">
        <t-icon name="rollback" />
        <span>撤销</span>
      </a>
      <a class="flex items-center flex-col" @click="onRedo">
        <t-icon name="rollfront" />
        <span>重做</span>
      </a>
      <a class="flex items-center flex-col" @dragstart="onAddShape($event, 'line')" @click="onAddShape($event, 'line')">
        <t-icon name="remove" />
        <span>直线</span>
      </a>
      <a class="flex items-center flex-col" @dragstart="onAddShape($event, 'text')" @click="onAddShape($event, 'text')">
        <t-icon name="textbox" />
        <span>文字</span>
      </a>
      <a class="flex items-center flex-col" @click="drawLine">
        <svg
          width="1em"
          height="1em"
          viewBox="0 0 1024 1024"
          xmlns="http://www.w3.org/2000/svg"
          :style="{
            color: isDrawLine ? ' #1677ff' : '',
          }"
        >
          <path
            d="M192 64a128 128 0 0 1 123.968 96H384a160 160 0 0 1 159.68 149.504L544 320v384a96 96 0 0 0 86.784 95.552L640 800h68.032a128 128 0 1 1 0 64.064L640 864a160 160 0 0 1-159.68-149.504L480 704V320a96 96 0 0 0-86.784-95.552L384 224l-68.032 0.064A128 128 0 1 1 192 64z m640 704a64 64 0 1 0 0 128 64 64 0 0 0 0-128zM192 128a64 64 0 1 0 0 128 64 64 0 0 0 0-128z"
            fill="currentColor"
          ></path>
        </svg>
        <span :style="{ color: isDrawLine ? ' #1677ff' : '' }">连线</span>
      </a>
      <a-dropdown v-model:visible="lineWidthVisible">
        <a class="flex items-center flex-col">
          <span class="flex items-center">
            {{ data.lineWidth }}&nbsp;
            <t-icon name="chevron-down-s" />
          </span>
          <span>线宽</span>
        </a>
        <template #overlay>
          <a-menu style="width: 220px">
            <a-menu-item key="1">
              <a-input-number v-model:value="data.lineWidth" style="width: 100%" @blur="getDataLineWidth" />
            </a-menu-item>
          </a-menu>
        </template>
      </a-dropdown>
      <a-dropdown overlayClassName="header-dropdown">
        <a class="flex items-center flex-col">
          <span class="flex items-center">
            <svg class="l-icon" aria-hidden="true">
              <use :xlink:href="lineTypes.find(item => item.value === currentLineType)?.icon"></use>
            </svg>
            <t-icon name="chevron-down-s" />
          </span>
          <span>
            {{ lineTypes.find(item => item.value === currentLineType)?.name }}
          </span>
        </a>
        <template #overlay>
          <a-menu style="width: 160px">
            <template v-for="(item, idx) in lineTypes" :key="idx">
              <a-menu-item>
                <div
                  class="middle w-full"
                  :class="[currentLineType == item.value ? 'active' : '']"
                  @click="changeLineType(item.value)"
                >
                  <div class="flex items-center justify-between">
                    <span>{{ item.name }}</span>
                    <svg class="l-icon" aria-hidden="true">
                      <use :xlink:href="item.icon"></use>
                    </svg>
                  </div>
                </div>
              </a-menu-item>
            </template>
          </a-menu>
        </template>
      </a-dropdown>
      <a-dropdown overlayClassName="header-dropdown">
        <a class="flex items-center flex-col">
          <span class="flex items-center">
            <svg class="l-icon" aria-hidden="true">
              <use :xlink:href="fromArrows.find(item => item.value === fromArrow)?.icon"></use>
            </svg>
            <t-icon name="chevron-down-s" />
          </span>
          <span>起点</span>
        </a>
        <template #overlay>
          <a-menu style="width: 160px">
            <template v-for="(item, idx) in fromArrows" :key="idx">
              <a-menu-item>
                <div class="middle w-full flex items-center" style="height: 30px" @click="changeFromArrow(item.value)">
                  <svg class="l-icon" aria-hidden="true">
                    <use :xlink:href="item.icon"></use>
                  </svg>
                </div>
              </a-menu-item>
            </template>
          </a-menu>
        </template>
      </a-dropdown>
      <a-dropdown overlayClassName="header-dropdown">
        <a class="flex items-center flex-col">
          <span class="flex items-center">
            <svg class="l-icon" aria-hidden="true">
              <use :xlink:href="toArrows.find(item => item.value === toArrow)?.icon"></use>
            </svg>
            <t-icon name="chevron-down-s" />
          </span>
          <span>终点</span>
        </a>
        <template #overlay>
          <a-menu style="width: 160px">
            <template v-for="(item, idx) in toArrows" :key="idx">
              <a-menu-item>
                <div class="middle w-full flex items-center" style="height: 30px" @click="changeToArrow(item.value)">
                  <svg class="l-icon" aria-hidden="true">
                    <use :xlink:href="item.icon"></use>
                  </svg>
                </div>
              </a-menu-item>
            </template>
          </a-menu>
        </template>
      </a-dropdown>
      <a class="flex items-center flex-col" :class="[isAutoAnchor == true ? 'active' : '']" @click="onAutoAnchor">
        <t-icon name="focus" />
        <span>自动锚点</span>
      </a>
      <a class="flex items-center flex-col" :class="[isDisableAnchor == true ? 'active' : '']" @click="onDisableAnchor">
        <t-icon name="map-aiming" />
        <span>
          {{ isDisableAnchor ? '显示锚点' : '禁用锚点' }}
        </span>
      </a>
    </div>
    <div class="head-right flex items-center">
      <a
        class="flex items-center flex-col"
        @click="setLocked"
        :style="{
          color: data.locked == 1 ? '#faad14' : data.locked == 2 ? 'red' : '',
        }"
      >
        <template v-if="data.locked == 0">
          <t-icon name="lock-off" />
          <span>编辑</span>
        </template>
        <template v-if="data.locked == 1">
          <t-icon name="lock-on" />
          <span>预览</span>
        </template>
        <template v-if="data.locked == 2">
          <t-icon name="lock-on" />
          <span>锁定</span>
        </template>
      </a>
      <a class="flex items-center flex-col" @click="onView()" title="运行查看">
        <t-icon name="play-circle" />
        <span>预览</span>
      </a>
      <template v-if="scale > 0">
        <a class="flex items-center flex-col">
          <span>{{ scale }}%</span>
          <span>视图</span>
        </a>
      </template>
      <a-tooltip title="100%视图" placement="bottom">
        <a class="flex items-center flex-col" @click="onScaleDefault">
          <t-icon name="refresh" />
          <span>还原</span>
        </a>
      </a-tooltip>
      <a class="flex items-center flex-col" @click="onScaleWindow" title="窗口大小">
        <t-icon name="fullscreen-exit" />
        <span>窗口大小</span>
      </a>
      <a class="flex items-center flex-col" title="文件管理" @click="openFileManager">
        <t-icon name="folder-open" />
        <span>文件管理</span>
      </a>
      <a class="flex items-center flex-col ai-btn" title="AI 助手" @click="onOpenAgentPanel">
        <t-icon name="robot" />
        <span>AI 助手</span>
      </a>
      <a class="flex items-center flex-col" @click="onSearch">
        <t-icon name="share" />
        <span>分享</span>
      </a>
      <a class="flex items-center flex-col" href="https://github.com/opendidi/mind" target="_blank">
        <t-icon name="logo-github" />
        <span>源代码</span>
      </a>
    </div>
    <ShareModal ref="shareModalRef" />
    <FileManager ref="fileManagerRef" :mode="'multiple'" />
  </div>
</template>

<script lang="ts" setup>
import { onMounted, onUnmounted, ref, watch, nextTick } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useCanvas } from '@/composables/useCanvas'
import { Pen, PenType, deepClone } from '@meta2d/core'
import FileSaver from 'file-saver'
import { message } from 'ant-design-vue'
import ShareModal from '../Share/index.vue'
import { useCommonStoreWithOut } from '@/store/modules/common'
import { apiBlueprintAdd, apiBlueprintModify } from '@/api/blueprint'
import { apiChatUploadFile } from '@/api/chat'
import FileManager from '@/components/FileManager/index.vue'

const emit = defineEmits(['openAgentPanel'])

const meta2d = useCanvas()

const router = useRouter()
const route = useRoute()

const fileManagerRef = ref(null)
const shareModalRef = ref(null)

const currentId = ref<string>((route.params.id as string) || '')
// 监听路由变换（从蓝图列表切换到另一张图纸时）同步 id
watch(
  () => route.params.id,
  newId => {
    if (newId && typeof newId === 'string') currentId.value = newId
  },
)
const data = ref({})

const isOnDrawLine = ref(false)

const dot = ref(false)

const isDrawingPencil = ref<boolean>(false)

// 连线时，自动选中节点锚点
const isAutoAnchor = ref<boolean>(false)

// 禁止显示锚点
const isDisableAnchor = ref<boolean>(false)

// 是否开启放大镜
const isShowMagnifier = ref<boolean>(false)

const visibleMap = ref<boolean>(false)

const isDrawLine = ref<boolean>(false)

const scale = ref(0)

const lineWidthVisible = ref(false)

const commonStore = useCommonStoreWithOut()
watch(
  () => commonStore.isSave,
  v => {
    v == '1' ? (dot.value = false) : (dot.value = true)
  },
  { immediate: true },
)

function scaleSubscriber(val: number) {
  scale.value = Math.round(val * 100)
}

const drawLine = () => {
  if (isDrawLine.value) {
    isDrawLine.value = false
    meta2d.finishDrawLine()
    meta2d.drawLine()
    meta2d.store.options.disableAnchor = true
  } else {
    isDrawLine.value = true
    meta2d.drawLine(meta2d.store.options.drawingLineName)
    meta2d.store.options.disableAnchor = false
  }
}

const lineTypes = [
  { name: '曲线', icon: '#l-curve2', value: 'curve' },
  { name: '线段', icon: '#l-polyline', value: 'polyline' },
  { name: '直线', icon: '#l-line', value: 'line' },
  { name: '脑图曲线', icon: '#l-mind', value: 'mind' },
]
const currentLineType = ref('curve')

const changeLineType = (value: string) => {
  currentLineType.value = value
  if (meta2d) {
    meta2d.store.options.drawingLineName = value
    meta2d.canvas.drawingLineName && (meta2d.canvas.drawingLineName = value)
    meta2d.store.active?.forEach(pen => {
      meta2d.updateLineType(pen, value)
    })
  }
}

/**
 * 获取线宽
 */
function getDataLineWidth() {
  if (data.value['lineWidth']) {
    meta2d.setValue({
      lineWidth: data.value.lineWidth,
    })
    useCommonStoreWithOut().setTopology(meta2d)
  }
}

const fromArrow = ref('')
const fromArrows = [
  { icon: '#l-line', value: '' },
  { icon: '#l-from-triangle', value: 'triangle' },
  { icon: '#l-from-diamond', value: 'diamond' },
  { icon: '#l-from-circle', value: 'circle' },
  { icon: '#l-from-lineDown', value: 'lineDown' },
  { icon: '#l-from-lineUp', value: 'lineUp' },
  { icon: '#l-from-triangleSolid', value: 'triangleSolid' },
  { icon: '#l-from-diamondSolid', value: 'diamondSolid' },
  { icon: '#l-from-circleSolid', value: 'circleSolid' },
  { icon: '#l-from-line', value: 'line' },
]
const toArrow = ref('')
const toArrows = [
  { icon: '#l-line', value: '' },
  { icon: '#l-to-triangle', value: 'triangle' },
  { icon: '#l-to-diamond', value: 'diamond' },
  { icon: '#l-to-circle', value: 'circle' },
  { icon: '#l-to-lineDown', value: 'lineDown' },
  { icon: '#l-to-lineUp', value: 'lineUp' },
  { icon: '#l-to-triangleSolid', value: 'triangleSolid' },
  { icon: '#l-to-diamondSolid', value: 'diamondSolid' },
  { icon: '#l-to-circleSolid', value: 'circleSolid' },
  { icon: '#l-to-line', value: 'line' },
]

const changeFromArrow = (value: string) => {
  fromArrow.value = value
  // 画布默认值
  meta2d.store.data.fromArrow = value
  // 活动层的箭头都变化
  if (meta2d.store.active) {
    meta2d.store.active.forEach((pen: Pen) => {
      if (pen.type === PenType.Line) {
        pen.fromArrow = value
        meta2d.setValue(
          {
            id: pen.id,
            fromArrow: pen.fromArrow,
          },
          {
            render: false,
          },
        )
      }
    })
    meta2d.render()
  }
}

const changeToArrow = (value: string) => {
  toArrow.value = value
  // 画布默认值
  meta2d.store.data.toArrow = value
  // 活动层的箭头都变化
  if (meta2d.store.active) {
    meta2d.store.active.forEach((pen: Pen) => {
      if (pen.type === PenType.Line) {
        pen.toArrow = value
        meta2d.setValue(
          {
            id: pen.id,
            toArrow: pen.toArrow,
          },
          {
            render: false,
          },
        )
      }
    })
    meta2d.render()
  }
}

const createBluePrint = () => {
  currentId.value = ''
  router.replace({ path: '/' })
  meta2d.open({
    name: '',
    pens: [],
    lines: [],
    background: 'rgba(255, 255, 255, 1)',
    color: '',
    penBackground: '',
    bkImage: '',
    gridColor: '',
    gridSize: '',
    gridRotate: '',
    ruleColor: '',
    initJs: '',
    https: [],
    thumbnail: '',
  })
  meta2d.store.data.locked = 0
  meta2d.store.data.fromArrow = ''
  meta2d.store.data.toArrow = 'triangleSolid'
  localStorage.removeItem('meta2d')
  window.dispatchEvent(new CustomEvent('meta2d:dataLoaded'))
}

const downloadJson = () => {
  const data: any = meta2d.data()
  FileSaver.saveAs(
    new Blob([JSON.stringify(data)], {
      type: 'text/plain;charset=utf-8',
    }),
    `${data.name || 'test'}.json`,
  )
}

const downloadPng = () => {
  let name = (meta2d.store.data as any).name
  if (name) {
    name += '.png'
  }
  meta2d.downloadPng(name)
}

// 判断该画笔 是否是组合为状态中 展示的画笔
function isShowChild(pen: any, store: any) {
  let selfPen = pen
  while (selfPen && selfPen.parentId) {
    const oldPen = selfPen
    selfPen = store.pens[selfPen.parentId]
    const showChildIndex = selfPen?.calculative?.showChild
    if (showChildIndex != undefined) {
      const showChildId = selfPen.children[showChildIndex]
      if (showChildId !== oldPen.id) {
        return false
      }
    }
  }
  return true
}

function downloadSvg() {
  if (!C2S) {
    message.error('请先加载canvas2svg.js插件')
    return
  }

  const rect: any = meta2d.getRect()
  rect.x -= 10
  rect.y -= 10
  const ctx = new C2S(rect.width + 20, rect.height + 20)
  ctx.textBaseline = 'middle'
  for (const pen of meta2d.store.data.pens) {
    if (pen.visible == false || !isShowChild(pen, meta2d.store)) {
      continue
    }
    meta2d.renderPenRaw(ctx, pen, rect)
  }

  let mySerializedSVG = ctx.getSerializedSvg()
  if (meta2d.store.data.background) {
    mySerializedSVG = mySerializedSVG.replace('{{bk}}', '')
    mySerializedSVG = mySerializedSVG.replace(
      '{{bkRect}}',
      `<rect x="0" y="0" width="100%" height="100%" fill="${meta2d.store.data.background}"></rect>`,
    )
  } else {
    mySerializedSVG = mySerializedSVG.replace('{{bk}}', '')
    mySerializedSVG = mySerializedSVG.replace('{{bkRect}}', '')
  }

  mySerializedSVG = mySerializedSVG.replace(/--le5le--/g, '&#x')

  const urlObject: any = (window as any).URL || window
  const export_blob = new Blob([mySerializedSVG])
  const url = urlObject.createObjectURL(export_blob)

  const a = document.createElement('a')
  a.setAttribute('download', `${(meta2d.store.data as any).name || 'le5le.meta2d'}.svg`)
  a.setAttribute('href', url)
  document.body.appendChild(a)
  a.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }))
  document.body.removeChild(a)
}

function onUndo() {
  meta2d.undo()
}

function onRedo() {
  meta2d.redo()
}

const onOpenMap = () => {
  visibleMap.value = visibleMap.value ? false : true
  if (visibleMap.value) {
    meta2d.showMap()
  } else {
    meta2d.hideMap()
  }
}

function onAddShape(event: DragEvent | MouseEvent, name: string) {
  event.stopPropagation()
  let data: any
  switch (name) {
    case 'text':
      // 构建一个文本图元
      data = {
        text: 'text',
        width: 100,
        height: 20,
        name: 'text',
        visible: true,
      }
      break
    case 'line':
      // 构建一个直线图元
      data = {
        anchors: [
          { id: '0', x: 1, y: 0 },
          { id: '1', x: 0, y: 1 },
        ],
        width: 100,
        height: 100,
        name: 'line',
        lineName: 'line',
        type: 1,
        visible: true,
      }
      break
  }
  if (!(event as DragEvent).dataTransfer) {
    // 支持点击画布添加
    meta2d.canvas.addCaches = deepClone([data])
  } else {
    // 支持拖拽添加
    ;(event as DragEvent).dataTransfer?.setData('Meta2d', JSON.stringify(data))
  }
}

const onScaleDefault = () => {
  meta2d.scale(1)
  meta2d.centerView()
}

const onScaleWindow = () => {
  meta2d.fitView()
}

async function onView() {
  // 先停止动画，避免数据波动
  meta2d.stopAnimate()
  const savedId = await onSave(true)
  if (!savedId) return
  // 跳转到预览页面
  router.push({
    path: '/preview/' + savedId,
    query: { r: Date.now() + '' },
  })
}

function onOpenAgentPanel() {
  emit('openAgentPanel')
}

function onSave(flag: boolean): Promise<string | false> | boolean {
  const canvasData: any = meta2d.data()
  if (!canvasData.pens.length) {
    message.error('无法保存，画布可能没有画笔/画布大小超出浏览器最大限制')
    return false
  }
  localStorage.setItem('meta2d', JSON.stringify(canvasData))
  commonStore.setTopology(meta2d)
  if (flag) {
    // 全量序列化（Meta2D 确保前向兼容）
    const params: any = { ...canvasData }

    // 确保 API 期望的字符串字段正确序列化
    if (typeof params.https !== 'string') params.https = JSON.stringify(params.https) || ''
    if (typeof params.pens !== 'string') params.pens = JSON.stringify(params.pens) || ''

    // 先截图 → 上传 → 获取缩略图URL，再保存
    return generateThumbnail().then(thumbnailUrl => {
      params.thumbnail = thumbnailUrl

      if (!currentId.value) {
        return apiBlueprintAdd(params)
          .then(res => {
            currentId.value = res.id
            commonStore.setIsSave('1')
            message.success('保存成功')
            router.replace({ path: '/' + res.id })
            canvasData['id'] = res.id
            return res.id as string
          })
          .catch(err => {
            message.error('保存失败，请重试')
            console.error('[onSave] add blueprint failed:', err)
            return false
          })
      } else {
        params.id = currentId.value
        return apiBlueprintModify(params)
          .then(() => {
            commonStore.setIsSave('1')
            message.success('保存成功')
            return params.id as string
          })
          .catch(async err => {
            // Modify may fail if blueprint was externally deleted — fallback to create
            currentId.value = ''
            try {
              const addRes = await apiBlueprintAdd(params)
              currentId.value = addRes.id
              commonStore.setIsSave('1')
              message.success('已保存为新图纸')
              router.replace({ path: '/' + addRes.id })
              return addRes.id as string
            } catch {
              message.error('保存失败，请重试')
              console.error('[onSave] modify → add fallback failed:', err)
              return false
            }
          })
      }
    })
  }
  return true
}

function generateThumbnail(): Promise<string> {
  return new Promise(resolve => {
    try {
      meta2d.toPng(
        20,
        async (blob: Blob | null) => {
          if (!blob) return resolve('')
          try {
            const file = new File([blob], `thumb_${Date.now()}.png`, { type: 'image/png' })
            const result = await apiChatUploadFile(file)
            resolve(result?.url || '')
          } catch {
            resolve('')
          }
        },
        false,
        400,
      )
    } catch {
      resolve('')
    }
  })
}

/**
 * 操作画布锁定
 */
function setLocked() {
  let { locked }: any = data.value
  let key = 0
  switch (locked) {
    case 0:
      key = 1
      break
    case 1:
      key = 2
      break
    case 2:
      key = 0
      break
  }
  data.value.locked = key //meta2d.store.data;
  onSave(false)
}

/**
 * 增加/删除锚点
 */
const onToggleAnchorMode = () => meta2d.toggleAnchorMode()

/**
 * 添加手柄
 */
const onAddAnchorHand = () => meta2d.addAnchorHand()

/**
 * 删除手柄
 */
const onRemoveAnchorHand = () => meta2d.removeAnchorHand()

/**
 * 钢笔绘制线条
 */
function onDrawLine() {
  if (!isOnDrawLine.value) {
    // 开始绘画：curve。除了curve，还有polyline、line、mind
    meta2d.drawLine('curve')
    isOnDrawLine.value = true
  } else {
    // 手动完成绘画
    meta2d.finishDrawLine()
    isOnDrawLine.value = false
  }
}

/**
 * 绘制铅笔
 */
function onDrawingPencil() {
  if (!isDrawingPencil.value) {
    meta2d.drawingPencil()
    isDrawingPencil.value = true
  } else {
    meta2d.stopPencil()
    isDrawingPencil.value = false
  }
}

/**
 * 禁止显示锚点
 */
function onDisableAnchor() {
  if (!isDisableAnchor.value) {
    meta2d.setOptions({
      disableAnchor: true,
    })
    isDisableAnchor.value = true
  } else {
    meta2d.setOptions({
      disableAnchor: false,
    })
    isDisableAnchor.value = false
  }
}

/**
 * 连线时，自动选中节点锚点
 */
function onAutoAnchor() {
  if (!isAutoAnchor.value) {
    meta2d.setOptions({
      autoAnchor: true,
    })
    isAutoAnchor.value = true
  } else {
    meta2d.setOptions({
      autoAnchor: false,
    })
    isAutoAnchor.value = false
  }
}

/**
 * 开启或关闭放大镜
 */
function onShowMagnifier() {
  if (!isShowMagnifier.value) {
    meta2d.showMagnifier()
    isShowMagnifier.value = true
  } else {
    meta2d.hideMagnifier()
    isShowMagnifier.value = false
  }
}

/**
 * 打开素材库
 */
function openFileManager() {
  const fileManager = fileManagerRef.value
  fileManager.visible = true
  nextTick(() => {
    fileManager.initMaterialFolder().then(res => {
      fileManager.selectedKeys = [res]
      fileManager.queryParam.parent_id = res
      fileManager.init()
    })
  })
}

/**
 * 分享
 */
function onSearch() {
  shareModalRef.value.visible = true
}

function onMeta2dReady() {
  if (!meta2d || !meta2d.store) {
    // meta2d global exists but store not yet initialized — retry once
    setTimeout(onMeta2dReady, 50)
    return
  }
  data.value = meta2d.store.data
  if (meta2d.store.data['lineWidth'] == undefined) {
    meta2d.store.data['lineWidth'] = 1
    meta2d.setValue({ lineWidth: 1 })
  }
  scaleSubscriber(meta2d.store.data.scale)
  meta2d.on('scale', scaleSubscriber)
  const options: any = meta2d.getOptions()
  isAutoAnchor.value = options.autoAnchor
}

onMounted(() => {
  window.addEventListener('meta2d:ready', onMeta2dReady, { once: true })
  // Safety timeout in case event was already dispatched before mount
  if (meta2d) {
    onMeta2dReady()
  } else {
    setTimeout(() => {
      if (meta2d) onMeta2dReady()
    }, 2000)
  }
  // Listen for external blueprint deletion — reset currentId so next save creates a new blueprint
  window.addEventListener('blueprint:deleted', onBlueprintDeleted)
})

onUnmounted(() => {
  if (meta2d) meta2d.off('scale', scaleSubscriber)
  window.removeEventListener('blueprint:deleted', onBlueprintDeleted)
})

function onBlueprintDeleted(e: Event) {
  const detail = (e as CustomEvent).detail as { id: string } | undefined
  if (detail && detail.id === currentId.value) {
    currentId.value = ''
    router.replace({ path: '/' })
  }
}
</script>

<style lang="less" scoped>
.app-header {
  position: relative;
  width: 100%;
  height: 50px;
  padding: 0 12px;
  background: #fff;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
  border-bottom: 1px solid #ddd;
  z-index: 3;

  .head-center {
    a {
      &.active,
      &:hover {
        color: #0c56eb;
      }
    }
  }

  .head-right {
    a {
      &:last-child {
        font-size: 18px;
      }
    }
  }

  a {
    margin: 0 8px;
    text-decoration: none;
    white-space: nowrap;
    color: #595959;

    span {
      font-size: 12px;
      &:first-child {
        height: 15px;
      }
    }

    &:hover {
      color: #4583ff;
    }

    svg {
      margin: 0;
      font-size: 15px;
    }

    .l-icon {
      width: 1em;
      height: 1em;
      vertical-align: -0.15em;
      fill: currentColor;
      overflow: hidden;
    }
  }

  svg {
    margin: 0 8px;

    &:hover {
      color: #4583ff;
      cursor: pointer;
    }
  }
}

.ant-dropdown {
  .ant-dropdown-menu {
    .l-icon {
      width: 1em;
      height: 1em;
      vertical-align: -0.15em;
      fill: currentColor;
      overflow: hidden;
    }
  }
}

.middle {
  &.active {
    color: #0c56eb;
  }
}

.ai-btn {
  .ai-icon {
    font-size: 16px !important;
  }

  &:hover {
    color: #1677ff !important;
    .ai-icon {
      transform: scale(1.15);
    }
  }
}
</style>
