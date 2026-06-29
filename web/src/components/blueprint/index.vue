<template>
  <a-modal
    v-model:visible="visible"
    title="图纸列表"
    width="800px"
    centered
    :destroyOnClose="true"
    :footer="null"
    :bodyStyle="{ maxHeight: '60vh', overflowY: 'auto', padding: '12px' }"
    wrapClassName="blueprint-modal"
  >
    <div class="blueprint-list">
      <template v-if="dataSource.length !== 0">
        <a-row :gutter="[12, 12]">
          <a-col v-for="item in dataSource" :key="item.id" :span="6">
            <div class="bp-card" @click="onOpen(item)">
              <div class="bp-thumb">
                <img v-if="item.thumbnail" :src="item.thumbnail" alt="" />
                <div v-else class="bp-thumb-placeholder">
                  <t-icon name="image" size="32px" />
                </div>
                <div class="bp-actions" @click.stop>
                  <a-popconfirm
                    title="确定删除该图纸？"
                    ok-text="删除"
                    cancel-text="取消"
                    placement="bottom"
                    @confirm="onDelete(item)"
                  >
                    <a-button size="small" danger type="text">
                      <DeleteOutlined />
                    </a-button>
                  </a-popconfirm>
                </div>
              </div>
              <div class="bp-name" :title="item.name">{{ item.name || '未命名' }}</div>
              <div class="bp-time">{{ item.created_at?.slice(0, 10) || '' }}</div>
            </div>
          </a-col>
        </a-row>
      </template>
      <template v-else>
        <a-empty description="暂无图纸" />
      </template>
    </div>

    <div class="bp-pagination" v-if="ipagination.total > 0">
      <a-pagination
        v-model:current="ipagination.current"
        v-model:pageSize="ipagination.pageSize"
        :total="ipagination.total"
        :showTotal="ipagination.showTotal"
        :showSizeChanger="true"
        :pageSizeOptions="['8', '12', '20', '32']"
        size="small"
        @change="onPageChange"
      />
    </div>
  </a-modal>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { message } from 'ant-design-vue'
import { DeleteOutlined } from '@ant-design/icons-vue'
import { useRouter } from 'vue-router'
import { apiBlueprintList, apiBlueprintDelete } from '@/api/blueprint'

const emit = defineEmits<{ (e: 'closed'): void }>()

const router = useRouter()
const visible = ref(false)

watch(visible, val => {
  if (!val) emit('closed')
})
const dataSource = ref<any[]>([])

const ipagination = ref({
  current: 1,
  pageSize: 8,
  total: 0,
  showTotal: (total: number) => `共 ${total} 条`,
})

watch(
  () => visible.value,
  val => {
    if (val) loadList()
  },
)

function loadList() {
  const { current, pageSize } = ipagination.value
  apiBlueprintList({ current, page_size: pageSize }).then((res: any) => {
    dataSource.value = res.list || []
    ipagination.value.current = res.current || current
    ipagination.value.total = res.total || 0
    ipagination.value.pageSize = res.page_size || pageSize
  })
}

function onPageChange(page: number, pageSize: number) {
  ipagination.value.current = page
  ipagination.value.pageSize = pageSize
  loadList()
}

function onOpen(item: any) {
  visible.value = false
  router.push({ path: '/' + item.id })
}

function onDelete(item: any) {
  apiBlueprintDelete({ id: item.id }).then((res: any) => {
    if (res.code === 200) {
      message.success('已删除')
      loadList()
      window.dispatchEvent(new CustomEvent('blueprint:deleted', { detail: { id: item.id } }))
    } else {
      message.error(res.message || '删除失败')
    }
  })
}

defineExpose({ visible })
</script>

<style lang="less" scoped>
.blueprint-list {
  min-height: 200px;
}

.bp-card {
  cursor: pointer;
  border: 1px solid #f0f0f0;
  border-radius: 8px;
  overflow: hidden;
  transition: box-shadow 0.2s;
  &:hover {
    box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
    border-color: #d9d9d9;
  }
}

.bp-thumb {
  position: relative;
  height: 120px;
  background: #fafafa;
  overflow: hidden;
  img {
    width: 100%;
    height: 100%;
    object-fit: cover;
  }
}

.bp-thumb-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #d9d9d9;
}

.bp-actions {
  position: absolute;
  top: 4px;
  right: 4px;
  opacity: 0;
  transition: opacity 0.15s;
  .bp-card:hover & {
    opacity: 1;
  }
}

.bp-name {
  padding: 6px 8px 0;
  font-size: 13px;
  font-weight: 500;
  color: #333;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.bp-time {
  padding: 2px 8px 8px;
  font-size: 11px;
  color: #999;
}

.bp-pagination {
  display: flex;
  justify-content: center;
  margin-top: 16px;
  padding-top: 8px;
  border-top: 1px solid #f0f0f0;
}
</style>
