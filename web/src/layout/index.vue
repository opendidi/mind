<!-- Main layout with left sidebar navigation -->
<template>
  <div class="app-layout">
    <aside class="layout-sidebar">
      <router-link to="/" class="sidebar-logo" title="Mind">
        <span class="logo-icon">🧠</span>
      </router-link>

      <nav class="sidebar-nav">
        <a-tooltip title="编辑器" placement="right">
          <router-link to="/" class="nav-item" :class="{ active: $route.path === '/' }">
            <t-icon name="edit-1" class="nav-icon" />
            <span class="nav-label">编辑器</span>
          </router-link>
        </a-tooltip>
        <a-tooltip title="AI 对话" placement="right">
          <router-link to="/chat" class="nav-item" :class="{ active: $route.path.startsWith('/chat') }">
            <span class="nav-ai-sparkle"></span>
            <span class="nav-label">AI 对话</span>
          </router-link>
        </a-tooltip>
      </nav>

      <div class="sidebar-bottom">
        <a-tooltip title="个人中心" placement="right">
          <router-link to="/profile" class="nav-item" :class="{ active: $route.path === '/profile' }">
            <t-icon name="user-circle" class="nav-icon" />
            <span class="nav-label">我的</span>
          </router-link>
        </a-tooltip>
        <a-tooltip title="退出登录" placement="right">
          <div class="nav-item logout-btn" @click="handleLogout">
            <t-icon name="logout" class="nav-icon" />
            <span class="nav-label">退出</span>
          </div>
        </a-tooltip>
      </div>
    </aside>

    <main class="layout-main">
      <AppMain />
    </main>

  </div>
</template>

<script setup lang="ts">
import { createVNode } from 'vue'
import { useRouter } from 'vue-router'
import { ExclamationCircleOutlined } from '@ant-design/icons-vue'
import { Modal } from 'ant-design-vue'
import { useUserStore } from '@/store/modules/user'
import AppMain from './AppMain.vue'

const router = useRouter()
const userStore = useUserStore()

function handleLogout() {
  Modal.confirm({
    title: '退出提示',
    icon: createVNode(ExclamationCircleOutlined),
    content: createVNode('div', { style: 'color:red;' }, '确定要退出吗？'),
    onOk() {
      userStore.logout().then(() => {
        router.push({ path: '/login' })
      })
    },
  })
}

</script>

<style lang="scss" scoped>
.app-layout {
  display: flex;
  width: 100%;
  height: 100vh;
  overflow: hidden;
}

.layout-sidebar {
  position: relative;
  width: 80px;
  min-width: 80px;
  height: 100%;
  padding: 10px 0;
  background: #1a1a1a;
  display: flex;
  flex-direction: column;
  align-items: center;
  z-index: 100;
}

.sidebar-logo {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 52px;
  height: 52px;
  margin-bottom: 16px;
  border-radius: 12px;
  background: linear-gradient(135deg, #4f46e5, #7c3aed);
  text-decoration: none;
  flex-shrink: 0;

  .logo-icon {
    font-size: 26px;
    line-height: 1;
  }
}

.sidebar-nav {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding-top: 8px;
}

.sidebar-bottom {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding-bottom: 4px;
}

.nav-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  width: 64px;
  padding: 10px 4px;
  border-radius: 8px;
  cursor: pointer;
  text-decoration: none;
  transition: background 0.15s;

  &:hover {
    background: rgba(255, 255, 255, 0.08);
  }

  &.active {
    background: rgba(255, 255, 255, 0.12);
  }
}

.nav-icon {
  font-size: 22px;
  color: #909090;
  margin-bottom: 2px;
  transition: color 0.15s;

  .nav-item:hover &,
  .nav-item.active & {
    color: #fff;
  }
}

.nav-ai-sparkle {
  display: block;
  width: 24px;
  height: 24px;
  margin-bottom: 2px;
  background: linear-gradient(135deg, #818cf8, #c084fc);
  clip-path: polygon(50% 0%, 62% 38%, 100% 50%, 62% 62%, 50% 100%, 38% 62%, 0% 50%, 38% 38%);
  animation: sparkle-pulse 2.4s ease-in-out infinite;
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

.nav-label {
  font-size: 10px;
  color: #909090;
  white-space: nowrap;
  transition: color 0.15s;

  .nav-item:hover &,
  .nav-item.active & {
    color: #fff;
  }
}

.logout-btn {
  .nav-icon,
  .nav-label {
    color: #909090;
  }

  &:hover {
    .nav-icon,
    .nav-label {
      color: #e53e3e;
    }
  }
}

.layout-main {
  flex: 1;
  min-width: 0;
  height: 100%;
  overflow: hidden;
}
</style>
