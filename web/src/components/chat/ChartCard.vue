<template>
  <div ref="chartRef" class="chart-card" :style="{ height: chartHeight }"></div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import * as echarts from 'echarts'

const props = defineProps<{
  option: Record<string, unknown>
  height?: string
}>()

const chartRef = ref<HTMLElement>()
const chartHeight = ref(props.height || '360px')
let chart: echarts.ECharts | null = null
let resizeObserver: ResizeObserver | null = null
let resizeTimer1: ReturnType<typeof setTimeout> | null = null
let resizeTimer2: ReturnType<typeof setTimeout> | null = null

function initChart() {
  if (!chartRef.value) return
  if (!chart) {
    chart = echarts.init(chartRef.value as any)
  }
  chart.setOption(props.option, true)
  // Catch late layout — parent may not have settled by nextTick
  resizeTimer1 = setTimeout(() => chart?.resize(), 50)
  resizeTimer2 = setTimeout(() => chart?.resize(), 200)
}

function handleResize() {
  chart?.resize()
}

watch(
  () => props.option,
  () => {
    nextTick(initChart)
  },
  { deep: true },
)

watch(
  () => props.height,
  h => {
    chartHeight.value = h || '360px'
    nextTick(() => chart?.resize())
  },
)

onMounted(() => {
  nextTick(initChart)
  if (chartRef.value && typeof ResizeObserver !== 'undefined') {
    resizeObserver = new ResizeObserver(() => chart?.resize())
    resizeObserver.observe(chartRef.value)
  } else {
    window.addEventListener('resize', handleResize)
  }
})

onBeforeUnmount(() => {
  if (resizeTimer1) clearTimeout(resizeTimer1)
  if (resizeTimer2) clearTimeout(resizeTimer2)
  resizeTimer1 = null
  resizeTimer2 = null
  window.removeEventListener('resize', handleResize)
  resizeObserver?.disconnect()
  resizeObserver = null
  chart?.dispose()
  chart = null
})
</script>

<style lang="scss" scoped>
.chart-card {
  width: 100%;
  min-width: 280px;
  max-width: 100%;
  min-height: 200px;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  background: #fff;
  margin: 4px 0;
  overflow: hidden;
}
</style>
