<!--
 * @Descripttion:
 * @version: 1.0.0
 * @Author: htang
 * @Date: 2023-11-07 19:56:27
 * @LastEditors: htang
 * @LastEditTime: 2026-06-25 14:22:26
-->
<template>
  <div id="meta2d"></div>
</template>

<script lang="ts" setup>
import { onMounted, onUnmounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { provideCanvas } from '@/composables/useCanvas'
import { message } from 'ant-design-vue'
import { apiBlueprintFind } from '@/api/blueprint'
import * as echarts from 'echarts'
import { register as registerEcharts } from '@meta2d/chart-diagram'
import { flowPens, flowAnchors } from '@meta2d/flow-diagram'
import { activityDiagram, activityDiagramByCtx } from '@meta2d/activity-diagram'
import { classPens } from '@meta2d/class-diagram'
import { sequencePens, sequencePensbyCtx } from '@meta2d/sequence-diagram'
import { formPens } from '@meta2d/form-diagram'
import { ftaPens, ftaPensbyCtx, ftaAnchors } from '@meta2d/fta-diagram'
import { Meta2d, register, registerAnchors, registerCanvasDraw } from '@meta2d/core'
import type { Pen } from '@meta2d/core'
import { useCommonStoreWithOut } from '@/store/modules/common'
import { removeOriginalData } from '@/utils/meta-storage'
import '@/assets/js/assets.le5lecdn.com_2d_canvas2svg.js'
import '@/assets/js/arrows.js'
import '@/assets/js/rg.js'
import { MetaPlugin } from '@/utils/plugin'
import { useSelection } from '@/services/selections'
import { useKeyboardShortcuts } from '@/composables/useKeyboardShortcuts'

const { select } = useSelection()
const commonStore = useCommonStoreWithOut()

let onStorageChange: ((e: StorageEvent) => void) | null = null
let resizeObserver: ResizeObserver | null = null
let meta2d: Meta2d | null = null

const route = useRoute()

function loadBlueprint(id: string) {
  if (!meta2d) return
  apiBlueprintFind({ id })
    .then((res: any) => {
      if (res?.data) {
        const bp = res.data
        meta2d.open({
          pens: bp.pens || [],
          name: bp.name || '',
          color: bp.color || '',
          penBackground: bp.penBackground || '',
          background: bp.background || '',
          bkImage: bp.bkImage || '',
          grid: bp.grid === '1' || bp.grid === true || undefined,
          gridColor: bp.gridColor || '',
          gridSize: bp.gridSize || '',
          gridRotate: bp.gridRotate || '',
          rule: bp.rule === '1' || bp.rule === true || undefined,
          ruleColor: bp.ruleColor || '',
          initJs: bp.initJs || '',
          https: bp.https || [],
          thumbnail: bp.thumbnail || '',
          locked: 0,
        })
        meta2d.store.data.fromArrow = ''
        meta2d.store.data.toArrow = 'triangleSolid'
        meta2d.fitView(true, 24)
        window.dispatchEvent(new CustomEvent('meta2d:dataLoaded'))
      } else {
        console.warn('[Editor] loadBlueprint: empty data for id=' + id)
        message.error('图纸加载失败')
      }
    })
    .catch((err: any) => {
      console.error('[Editor] loadBlueprint failed:', err)
      message.error('图纸加载失败')
    })
}

onMounted(() => {
  const meta2dOptions: any = {
    background: 'transparent',
  }
  if (window.location.pathname.indexOf('preview') !== -1) {
    meta2dOptions['rule'] = false
  } else {
    meta2dOptions['rule'] = true
  }
  meta2d = new Meta2d('meta2d', meta2dOptions)
  provideCanvas(meta2d)
  window.dispatchEvent(new CustomEvent('meta2d:ready'))

  // Register keyboard shortcuts (Delete, Ctrl+C/V/A/D, arrows, Escape)
  useKeyboardShortcuts(meta2d)

  // 按需注册图形库，以下为自带基础图形库
  register(flowPens())
  registerAnchors(flowAnchors())
  register(activityDiagram())
  registerCanvasDraw(activityDiagramByCtx())
  register(classPens())
  register(sequencePens())
  registerCanvasDraw(sequencePensbyCtx())
  registerCanvasDraw(formPens())
  register(ftaPens())
  registerCanvasDraw(ftaPensbyCtx())
  registerAnchors(ftaAnchors())

  // 注册 ECharts 图表画笔
  registerEcharts(echarts)

  // 初始化插件
  initPlugin()

  // Initial blueprint load is handled by parent Index.vue's onInit()
  // Route-change loading is handled by the watch below

  // Register custom tools immediately — meta2dTools is already available
  // from synchronously loaded arrows.js and canvas2svg.js
  if (window?.meta2dTools) {
    window?.registerToolsNew()
  }

  // Cross-tab sync: reload canvas when another tab (e.g. chat) modifies localStorage
  onStorageChange = (e: StorageEvent) => {
    if (e.key === 'meta2d' && e.newValue) {
      try {
        const data = JSON.parse(e.newValue)
        if (!data.locked) data.locked = 0
        meta2d.open(data)
        window.dispatchEvent(new CustomEvent('meta2d:dataLoaded'))
      } catch {
        /* ignore malformed data */
      }
    }
  }
  window.addEventListener('storage', onStorageChange)

  // Auto-resize canvas when container size changes (e.g. chat panel toggle)
  const container = document.getElementById('meta2d')
  if (container) {
    resizeObserver = new ResizeObserver(() => {
      if (meta2d?.canvas) meta2d.resize()
    })
    resizeObserver.observe(container)
  }

  meta2d.on('active', active)
  meta2d.on('inactive', inactive)

  meta2d.socketFn = (message: unknown, _context: unknown) => {
    if (!message) return true
    let info: Record<string, unknown> | undefined
    try {
      info = typeof message === 'string' ? JSON.parse(message) : (message as Record<string, unknown>)
    } catch {
      return true
    }
    if (info && typeof info === 'object' && 'data' in info) {
      const payload = info.data as Record<string, unknown> | undefined
      if (payload && payload['data']) {
        let dataList: unknown[]
        try {
          const raw = payload['data']
          dataList = typeof raw === 'string' ? JSON.parse(raw) : (raw as unknown[])
        } catch {
          return true
        }
        let hasUpdate = false
        dataList.forEach((item: any) => {
          if (item['dot'] === 0) {
            item['id'] = `a${item['dot']}`
          } else {
            item['id'] = item['dot']
          }
          if (item['vtype'] === 'FLOAT') {
            let data = parseFloat(item['value']).toFixed(2)
            item['text'] = Number(data)
          } else {
            item['text'] = item['value']
          }
          if (item['id'] === 6) {
            item['progress'] = item['value'] / 10
          }
          meta2d.setValue({ ...item }, { render: false })
          hasUpdate = true
        })
        if (hasUpdate) {
          meta2d.render()
          // Sync to localStorage so data persists across refresh
          localStorage.setItem('meta2d', JSON.stringify(meta2d.data()))
          // Store variable data for binding UI (updates store + localStorage)
          commonStore.setVariableData(dataList)
          // Mark save state as dirty
          commonStore.setIsSave('0')
        }
      }
    }
    return true
  }
})

// 监听路由变化，切换图纸
watch(
  () => route.params.id,
  newId => {
    if (newId && typeof newId === 'string') {
      loadBlueprint(newId)
    }
  },
)

function active(pens?: Pen[]) {
  select(pens)
}

function inactive() {
  select()
}

/**
 * 初始化插件
 */
function initPlugin() {
  let target = 'mindNode'
  let metaplugin = new MetaPlugin({})
  metaplugin.initPlugin(meta2d, target, {})
}

onUnmounted(() => {
  if (onStorageChange) window.removeEventListener('storage', onStorageChange)
  if (resizeObserver) resizeObserver.disconnect()
  if (meta2d) {
    meta2d.off('active', active)
    meta2d.off('inactive', inactive)
    meta2d.destroy()
  }
  // 删除原始数据
  removeOriginalData()
})
</script>

<style lang="less" scoped>
#meta2d {
  position: relative;
  width: 100%;
  height: 100%;
  .toolbox {
    position: absolute;
    display: none;
    width: 100px;
    height: 30px;
    background: red;
    z-index: 10000;
  }
}
</style>