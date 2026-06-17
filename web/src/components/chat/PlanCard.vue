<!-- Plan card — Agent execution plan display -->
<template>
  <div v-if="plan && plan.steps.length > 0" class="plan-card">
    <div class="plan-header">
      <span class="plan-icon">📋</span>
      <span class="plan-title">执行计划</span>
      <span class="plan-risk" :class="plan.risk">
        {{ riskLabel }}
      </span>
    </div>
    <div class="plan-goal">{{ plan.goal }}</div>
    <div class="plan-steps">
      <template v-for="(step, si) in plan.steps" :key="step.id">
        <div
          class="plan-step"
          :class="{
            active: step.status === 'active',
            done: step.status === 'done',
            failed: step.status === 'failed',
          }"
        >
          <span class="step-num">
            <CheckCircleFilled v-if="step.status === 'done'" />
            <CloseCircleFilled v-else-if="step.status === 'failed'" />
            <LoadingOutlined v-else-if="step.status === 'active'" spin />
            <span v-else>{{ si + 1 }}</span>
          </span>
          <span class="step-desc">{{ step.desc }}</span>
          <span v-if="step.tool" class="step-tool-tag">{{ step.tool }}</span>
          <span v-if="step.confirm" class="step-confirm-tag">需确认</span>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import {
  CheckCircleFilled,
  CloseCircleFilled,
  LoadingOutlined,
} from '@ant-design/icons-vue'

export interface PlanStep {
  id: string
  desc: string
  tool: string | null
  confirm: boolean
  status?: 'pending' | 'active' | 'done' | 'failed'
}

export interface PlanData {
  goal: string
  steps: PlanStep[]
  risk: string
}

const props = defineProps<{
  plan: PlanData | null
}>()

const riskLabel = computed(() => {
  const map: Record<string, string> = {
    high: '高风险',
    medium: '中风险',
    low: '低风险',
  }
  return map[props.plan?.risk || ''] || '低风险'
})
</script>

<style lang="scss" scoped>
.plan-card {
  max-width: 768px;
  margin: 0 auto 16px;
  padding: 16px 20px;
  background: linear-gradient(135deg, #eef2ff, #faf5ff);
  border: 1px solid #c7d2fe;
  border-radius: 14px;

  .plan-header {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 8px;
    .plan-icon { font-size: 18px; }
    .plan-title { font-weight: 700; font-size: 14px; color: #4338ca; }
    .plan-risk {
      font-size: 11px; padding: 1px 8px; border-radius: 10px; font-weight: 500; margin-left: auto;
      &.low { background: #d1fae5; color: #065f46; }
      &.medium { background: #fef3c7; color: #92400e; }
      &.high { background: #fee2e2; color: #991b1b; }
    }
  }

  .plan-goal {
    font-size: 13px; color: #475569; margin-bottom: 12px; padding-left: 26px;
  }

  .plan-steps .plan-step {
    display: flex; align-items: center; gap: 10px;
    padding: 7px 10px; border-radius: 8px; font-size: 13px; transition: background 0.2s;
    &.active { background: rgba(79, 70, 229, 0.08); }
    &.done { opacity: 0.7; }
    .step-num {
      width: 22px; height: 22px; display: flex; align-items: center; justify-content: center;
      font-size: 12px; font-weight: 600; color: #6366f1; background: #e0e7ff;
      border-radius: 50%; flex-shrink: 0;
      :deep(.anticon) { font-size: 16px; }
    }
    &.done .step-num { color: #10b981; background: #d1fae5; }
    &.failed .step-num { color: #ef4444; background: #fee2e2; }
    &.active .step-num { color: #6366f1; background: #c7d2fe; }
    .step-desc { flex: 1; color: #334155; }
    .step-tool-tag {
      font-size: 10px; padding: 1px 6px; border-radius: 6px;
      background: #e0e7ff; color: #4338ca;
      font-family: "Fira Code", "Consolas", monospace;
    }
    .step-confirm-tag {
      font-size: 10px; padding: 1px 6px; border-radius: 6px;
      background: #fef3c7; color: #b45309;
    }
  }
}
</style>
