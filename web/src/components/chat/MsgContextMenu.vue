<!-- Right-click context menu — Copy / Quote / Delete -->
<template>
  <a-dropdown :trigger="['contextmenu']" :visible="visible" @visibleChange="onVisibleChange">
    <div @contextmenu.prevent="onContextMenu" style="display: contents">
      <slot />
    </div>
    <template #overlay>
      <a-menu @click="onMenuClick">
        <a-menu-item key="copy"> <CopyOutlined /><span style="margin-left: 8px">复制</span> </a-menu-item>
        <a-menu-item v-if="showQuote" key="quote">
          <MessageOutlined /><span style="margin-left: 8px">引用</span>
        </a-menu-item>
        <a-menu-divider />
        <a-menu-item v-if="showDelete" key="delete" danger>
          <DeleteOutlined /><span style="margin-left: 8px">删除</span>
        </a-menu-item>
      </a-menu>
    </template>
  </a-dropdown>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { CopyOutlined, DeleteOutlined, MessageOutlined } from '@ant-design/icons-vue'

const props = withDefaults(
  defineProps<{
    showQuote?: boolean
    showDelete?: boolean
  }>(),
  {
    showQuote: true,
    showDelete: false,
  },
)

const emit = defineEmits<{
  copy: []
  quote: []
  delete: []
}>()

const visible = ref(false)

function onContextMenu() {
  visible.value = true
}

function onVisibleChange(val: boolean) {
  visible.value = val
}

function onMenuClick({ key }: { key: string }) {
  visible.value = false
  if (key === 'copy') emit('copy')
  else if (key === 'quote') emit('quote')
  else if (key === 'delete') emit('delete')
}
</script>
