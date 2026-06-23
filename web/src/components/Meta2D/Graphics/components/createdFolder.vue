<!--
 * @Descripttion:
 * @version: 1.0.0
 * @Author: htang
 * @Date: 2024-09-25 12:00:26
 * @LastEditors: htang
 * @LastEditTime: 2025-08-18 19:52:58
-->
<template>
  <a-modal
    v-model:visible="visible"
    centered
    width="30%"
    :destroyOnClose="true"
    cancelText="取消"
    okText="确定"
    title="新建文件夹"
    @ok="onFinish"
    @cancel="visible = false"
  >
    <a-form ref="formRef" :model="model" :rules="rules">
      <a-form-item label="文件夹名称" name="name">
        <a-input v-model:value="model.name" placeholder="请输入文件夹名称" />
      </a-form-item>
    </a-form>
  </a-modal>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { message } from 'ant-design-vue'
import { useCommonStore } from '@/store/modules/common'

const visible = ref(false)

const emit = defineEmits(['oks'])

const formRef = ref(null)

const model = ref({
  name: '',
  parent_id: '',
})

const rules = ref({
  name: [{ required: true, message: '请输入文件夹名称' }],
})

watch(
  () => visible.value,
  val => {
    if (!val) {
      formRef.value.resetFields()
    }
  },
)

function onFinish() {
  formRef.value.validate().then(() => {
    const name = model.value.name.trim()
    if (!name) return
    let folders = useCommonStore().customFolders || []
    if (folders.some((f: any) => f.name === name)) {
      message.warning('文件夹名称已存在')
      return
    }
    folders = [...folders, { name, items: [] }]
    useCommonStore().setCustomFolders(folders)
    emit('oks', folders)
    visible.value = false
  })
}

defineExpose({
  visible,
})
</script>
