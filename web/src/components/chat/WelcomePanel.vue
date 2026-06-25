<!-- Welcome panel — empty state with suggestion cards -->
<template>
  <div class="welcome-area">
    <div class="welcome-logo">
      <i class="icon-ds block ds-big"></i>
    </div>
    <div class="welcome-title">我是 J.A.R.V.I.S.，你的智能图形助手</div>
    <div class="welcome-subtitle">可以帮你创建和编辑图形、管理蓝图、生成思维导图，随时问我任何问题</div>
    <div class="suggestion-cards">
      <template v-for="sg in suggestions" :key="sg.label">
        <div class="suggestion-card" @click="$emit('suggest', sg.message)">
          <div class="sg-icon">{{ sg.icon }}</div>
          <div class="sg-label">{{ sg.label }}</div>
          <div class="sg-desc">{{ sg.desc }}</div>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
defineEmits<{ suggest: [text: string] }>()

const suggestions = [
  {
    icon: '🎨',
    label: '创建图形',
    desc: '帮我创建一个流程图',
    message: '帮我创建一个用户登录流程图，包含成功和失败两个分支',
  },
  {
    icon: '🧠',
    label: '思维导图',
    desc: '帮我生成一个思维导图',
    message: '帮我生成一个关于项目管理的思维导图，覆盖计划、执行、监控、收尾',
  },
  {
    icon: '📋',
    label: '管理图纸',
    desc: '查看和搜索已有的图纸',
    message: '帮我列出当前所有图纸，并按创建时间排序',
  },
  {
    icon: '📐',
    label: '排版布局',
    desc: '自动调整图形布局',
    message: '帮我自动排列当前画布上的所有节点，使用树形布局',
  },
]
</script>

<style lang="scss" scoped>
$primary: #4f46e5;
$text: #1e293b;
$text-secondary: #64748b;
$text-muted: #94a3b8;
$border: #e2e8f0;

.icon-ds {
  display: block;
  background: linear-gradient(135deg, #818cf8, #c084fc);
  clip-path: polygon(50% 0%, 62% 38%, 100% 50%, 62% 62%, 50% 100%, 38% 62%, 0% 50%, 38% 38%);
  animation: sparkle-pulse 2.4s ease-in-out infinite;
  width: 28px;
  height: 28px;

  &.ds-big {
    width: 56px;
    height: 56px;
  }
}

@keyframes sparkle-pulse {
  0%,
  100% {
    opacity: 0.7;
    transform: scale(0.95);
  }
  50% {
    opacity: 1;
    transform: scale(1.05);
  }
}

.welcome-area {
  text-align: center;
  padding: 60px 20px 40px;
  max-width: 640px;
  margin: 0 auto;
  .welcome-logo {
    margin-bottom: 16px;
    display: flex;
    justify-content: center;
  }
  .welcome-title {
    font-size: 22px;
    font-weight: 700;
    color: $text;
    margin-bottom: 8px;
  }
  .welcome-subtitle {
    font-size: 14px;
    color: $text-secondary;
    margin-bottom: 32px;
  }
}

.suggestion-cards {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  max-width: 520px;
  margin: 0 auto;

  .suggestion-card {
    background: #f8fafc;
    border: 1px solid $border;
    border-radius: 12px;
    padding: 16px;
    cursor: pointer;
    text-align: left;
    transition: all 0.2s;

    &:hover {
      border-color: $primary;
      box-shadow: 0 2px 12px rgba($primary, 0.08);
      transform: translateY(-1px);
    }
    .sg-icon {
      font-size: 22px;
      margin-bottom: 6px;
    }
    .sg-label {
      font-size: 14px;
      font-weight: 600;
      color: $text;
      margin-bottom: 2px;
    }
    .sg-desc {
      font-size: 12px;
      color: $text-muted;
    }
  }
}
</style>
