<template>
  <div v-if="plan && plan.mode === 'dag'" class="plan-card">
    <div class="plan-header">
      <span class="plan-icon">📋</span>
      <span class="plan-title">执行计划</span>
      <a-tag :color="riskColor" size="small">{{ plan.risk || 'low' }}</a-tag>
    </div>
    <div class="plan-goal">{{ plan.goal }}</div>
    <div class="plan-steps">
      <div
        v-for="node in plan.nodes"
        :key="node.id"
        class="plan-step"
        :class="`step-${node.status || 'pending'}`"
      >
        <span class="step-status">
          <span v-if="node.status === 'completed'">✅</span>
          <span v-else-if="node.status === 'running'">⏳</span>
          <span v-else-if="node.status === 'failed'">❌</span>
          <span v-else>○</span>
        </span>
        <span class="step-id">{{ node.id }}</span>
        <span class="step-desc">{{ node.desc }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type { PlanInfo } from './AgentStreamHandler';

const props = defineProps<{
  plan: PlanInfo | null;
}>();

const riskColor = computed(() => {
  switch (props.plan?.risk) {
    case 'high': return 'red';
    case 'medium': return 'orange';
    default: return 'green';
  }
});
</script>

<style scoped lang="less">
.plan-card {
  background: #fff;
  border: 1px solid #e8e8e8;
  border-radius: 8px;
  padding: 12px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.06);
}

.plan-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}

.plan-icon {
  font-size: 16px;
}

.plan-title {
  font-weight: 600;
  font-size: 14px;
}

.plan-goal {
  font-size: 13px;
  color: #555;
  margin-bottom: 8px;
  padding-bottom: 8px;
  border-bottom: 1px solid #f0f0f0;
}

.plan-steps {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.plan-step {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 13px;

  &.step-running {
    background: #f0f5ff;
  }

  &.step-completed {
    background: #f6ffed;
  }

  &.step-failed {
    background: #fff2f0;
  }
}

.step-status {
  font-size: 12px;
  width: 18px;
  text-align: center;
}

.step-id {
  font-family: monospace;
  font-size: 12px;
  color: #888;
  min-width: 24px;
}

.step-desc {
  color: #333;
}
</style>
