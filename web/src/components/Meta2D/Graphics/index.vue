<template>
  <div class="graphics">
    <a-tabs v-model:activeKey="tabsActiveKey" size="small" :tabBarGutter="12" :centered="true">
      <a-tab-pane key="1" tab="系统组件">
        <div class="p-3">
          <a-input
            v-model:value="keyword"
            @input="debouncedFilter"
            :disabled="activeKey == 2"
            placeholder="输入关键词搜索"
          />
        </div>
        <div class="scroll">
          <a-collapse
            v-model:activeKey="activeKey"
            :defaultExpandAll="true"
            expand-icon-position="right"
            accordion
            ghost
          >
            <template v-for="(item, idx) in graphicGroupsList" :key="idx">
              <a-collapse-panel :forceRender="true" v-show="item.show">
                <template #header>
                  <div class="flex items-center">
                    <template v-if="activeKey == idx">
                      <folder-open-outlined style="margin: 0 6px 0 0" />
                    </template>
                    <template v-else>
                      <folder-outlined style="margin: 0 6px 0 0" />
                    </template>
                    <a-tooltip placement="right">
                      <template #title>
                        <span>{{ item.name }}</span>
                      </template>
                      <span class="group-name" :title="item.name">
                        {{ item.name }}
                      </span>
                    </a-tooltip>
                    <span class="group-total">
                      {{ '(' + item.list.length + ')' }}
                    </span>
                  </div>
                </template>
                <ul class="flex items-center flex-wrap">
                  <template v-for="(vo, i) in item.list" :key="i">
                    <li
                      class="graphic flex justify-center items-center"
                      :draggable="true"
                      @dragstart="dragStart($event, vo)"
                      @click.prevent="dragStart($event, vo)"
                      :title="vo.name"
                    >
                      <template v-if="vo.icon.indexOf('iconfont') !== -1">
                        <i :class="vo.icon"></i>
                      </template>
                      <template v-else-if="vo.icon.indexOf('video-camera') !== -1">
                        <Icon :title="vo.name" :name="vo.icon" style="font-size: 30px" />
                      </template>
                      <template v-else-if="vo.subClassName == '箭头'">
                        <div class="flex items-center justify-center" v-html="vo.svg"></div>
                      </template>
                      <template v-else-if="vo.subClassName == '拓扑图未分类'">
                        <div class="flex items-center justify-center" v-html="vo.svg"></div>
                      </template>
                      <template v-else-if="vo.iconFamily == 't-icon'">
                        <t-icon :name="vo.icon" />
                      </template>
                      <template v-else>
                        <svg class="l-icon" aria-hidden="true">
                          <use :xlink:href="`#${vo.icon}`"></use>
                        </svg>
                      </template>
                    </li>
                  </template>
                </ul>
              </a-collapse-panel>
            </template>
          </a-collapse>
        </div>
        <div class="more-graphical flex justify-center items-center p-2">
          <a-button class="w-full" @click="openGraphics">图形库管理</a-button>
        </div>
      </a-tab-pane>
      <a-tab-pane key="2" tab="我的组件" force-render>
        <div class="mkdir-head flex items-center pb-2" @click="openCreatedFolder">
          <folder-add-outlined />
          <span>新建文件夹</span>
        </div>
        <template v-if="directoryList.length !== 0">
          <a-collapse
            v-model:activeKey="directoryKey"
            :defaultExpandAll="true"
            expand-icon-position="right"
            accordion
            ghost
          >
            <template v-for="(vo, idx) in directoryList" :key="idx">
              <a-collapse-panel :forceRender="true">
                <template #header>
                  <span>{{ vo.name }}</span>
                </template>
              </a-collapse-panel>
            </template>
          </a-collapse>
        </template>
        <template v-else>
          <a-empty description="暂没数据" />
        </template>
      </a-tab-pane>
      <a-tab-pane key="3" tab="图纸" force-render>
        <a-spin :spinning="blueprintLoading" tip="加载中...">
          <template v-if="blueprintList.length !== 0">
            <div class="bp-toolbar" v-if="blueprintList.length > 0">
              <a-checkbox :indeterminate="indeterminate" :checked="checkAll" @change="onCheckAllChange">
                全选
              </a-checkbox>
              <a-button v-if="selectedIds.size > 0" size="small" danger @click.stop="onBatchDelete">
                删除 ({{ selectedIds.size }})
              </a-button>
            </div>
            <div class="blueprint-grid">
              <template v-for="item in blueprintList" :key="item.id">
                <div class="bp-card" :class="{ 'bp-card-selected': selectedIds.has(item.id) }">
                  <div class="bp-check" @click.stop="onToggleSelect(item.id)">
                    <a-checkbox :checked="selectedIds.has(item.id)" />
                  </div>
                  <div class="bp-card-body" @click="onOpenBlueprint(item)">
                    <div class="bp-thumb">
                      <img v-if="item.thumbnail" :src="item.thumbnail" alt="" />
                      <template v-else>
                        <t-icon name="image" size="28px" class="bp-placeholder-icon" />
                      </template>
                    </div>
                    <div class="bp-name" :title="item.name">
                      {{ item.name || '未命名' }}
                    </div>
                    <div class="bp-time">
                      {{ item.created_at?.slice(0, 10) || '' }}
                    </div>
                  </div>
                  <div class="bp-card-actions" @click.stop>
                    <delete-outlined class="bp-delete-btn" @click="onDeleteBlueprint(item)" />
                  </div>
                </div>
              </template>
            </div>
          </template>
          <template v-else>
            <div class="pt-5">
              <a-empty description="暂无图纸" />
            </div>
          </template>
        </a-spin>
      </a-tab-pane>
    </a-tabs>
    <MoreModal ref="moreModalRef" @oks="handleGraphicGroups" />
    <CreatedFolder ref="createdFolderRef" @oks="onFolderCreated" />
  </div>
</template>

<script lang="ts" setup>
import { ref, computed, watch, nextTick, onMounted, onUnmounted, createVNode } from 'vue'
import { useCanvas } from '@/composables/useCanvas'
import { message, Modal } from 'ant-design-vue'
import { FolderOutlined, FolderOpenOutlined, FolderAddOutlined, DeleteOutlined, ExclamationCircleOutlined } from '@ant-design/icons-vue'
import { GRAPHIC_GROUPS as graphicGroups } from '@/utils/graphicGroups.ts'
import { MoreModal, CreatedFolder } from './components/index.ts'
import { useCommonStore } from '@/store/modules/common'
import { Icon } from 'tdesign-icons-vue-next'
import { useRouter } from 'vue-router'
import { apiBlueprintList, apiBlueprintDelete } from '@/api/blueprint'

const meta2d = useCanvas()

// 原数据
const originalGraphicGroups = graphicGroups

const graphicGroupsList = ref(graphicGroups)

const moreModalRef = ref(null)
const createdFolderRef = ref(null)

const tabsActiveKey = ref('1')

const activeKey = ref(0)

// 文件夹列表
const directoryList = ref(useCommonStore().customFolders || [])

// 折叠key
const directoryKey = ref('')

// 路由
const router = useRouter()

// 图纸列表
const blueprintList = ref<any[]>([])
const blueprintLoading = ref(false)
const selectedIds = ref<Set<string>>(new Set())

const checkAll = computed(() => {
  return blueprintList.value.length > 0 && selectedIds.value.size === blueprintList.value.length
})

const indeterminate = computed(() => {
  return selectedIds.value.size > 0 && selectedIds.value.size < blueprintList.value.length
})

function onCheckAllChange() {
  if (checkAll.value) {
    selectedIds.value = new Set()
  } else {
    selectedIds.value = new Set(blueprintList.value.map((b: any) => b.id))
  }
}

function onToggleSelect(id: string) {
  const next = new Set(selectedIds.value)
  if (next.has(id)) {
    next.delete(id)
  } else {
    next.add(id)
  }
  selectedIds.value = next
}

function onBatchDelete() {
  const ids = [...selectedIds.value]
  if (ids.length === 0) return
  Modal.confirm({
    title: '批量删除确认',
    icon: createVNode(ExclamationCircleOutlined),
    content: createVNode('div', { style: 'color:red;' }, `确定要删除选中的 ${ids.length} 张图纸吗？删除后不可恢复。`),
    okText: '确定删除',
    okType: 'danger',
    cancelText: '取消',
    onOk() {
      const promises = ids.map(id => apiBlueprintDelete({ id }))
      return Promise.allSettled(promises)
        .then(results => {
          let successCount = 0
          results.forEach((r: any, i: number) => {
            if (r.status === 'fulfilled' && r.value?.code === 200) {
              window.dispatchEvent(new CustomEvent('blueprint:deleted', { detail: { id: ids[i] } }))
              successCount++
            }
          })
          if (successCount > 0) {
            message.success(`已删除 ${successCount} 张图纸`)
          }
          selectedIds.value = new Set()
          loadBlueprints()
        })
    },
  })
}

// 过滤值
const keyword = ref('')

// 防抖定时器
let debounceTimer: ReturnType<typeof setTimeout> | null = null

const dragStart = (
  e: DragEvent | MouseEvent,
  elem: { name: string; data: any; icon: string; iconFamily?: string; subClassName?: string; svg?: string },
) => {
  let commonStore = useCommonStore()
  if (!elem) {
    return
  }
  e.stopPropagation()
  // 拖拽事件
  if (e instanceof DragEvent) {
    commonStore.setIsSave('0')
    e.dataTransfer?.setData('Meta2d', JSON.stringify(elem.data))
  } else {
    // 支持单击添加图元。平板模式
    meta2d.canvas.addCaches = [elem.data]
  }
}

function openGraphics() {
  moreModalRef.value.visible = true
  nextTick(() => {
    moreModalRef.value.init()
  })
}

/**
 * 显示/隐藏回调后处理左侧栏是否显示或者隐藏
 */
function handleGraphicGroups() {
  let graphicsKey = useCommonStore().graphics
  let keys = Object.keys(graphicsKey)
  let array: any = []
  Object.values(graphicsKey).map((_, idx) => {
    if (!_) {
      array.push(keys[idx])
    }
  })
  graphicGroupsList.value.map(_ => {
    if (array.includes(_.name)) {
      _.show = false
    } else {
      _.show = true
    }
  })
}

/**
 * 防抖筛选
 */
function debouncedFilter() {
  if (debounceTimer) clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => {
    filterGraphicGroups()
  }, 200)
}

/**
 * 筛选过滤组件
 */
function filterGraphicGroups() {
  const key = keyword.value
  if (key) {
    const list = originalGraphicGroups
    const array: typeof graphicGroups = []
    for (let i = 0; i < list.length; i++) {
      if (list[i].name.indexOf(key) !== -1) {
        array.push({
          ...list[i],
        })
      }
      const foundInList = list[i].list.filter(item => {
        const { name } = item
        if (name.indexOf('http') !== -1) {
          const decodedStr = decodeURIComponent(name)
          if (decodedStr.indexOf(key) !== -1) {
            return true
          }
        } else {
          if (name.indexOf(key) !== -1) {
            return true
          }
        }
        return false
      })
      if (foundInList.length !== 0) {
        array.push({
          ...list[i],
          list: [...foundInList],
        })
      }
    }
    graphicGroupsList.value = array
  } else {
    graphicGroupsList.value = graphicGroups
  }
}

const openCreatedFolder = () => {
  createdFolderRef.value.visible = true
}

const onFolderCreated = (folders: Array<{ name: string; list: unknown[] }>) => {
  directoryList.value = folders
}

function loadBlueprints() {
  blueprintLoading.value = true
  apiBlueprintList({ current: 1, page_size: 50 })
    .then(res => {
      blueprintList.value = res.list || []
    })
    .catch(() => {
      message.error('加载图纸列表失败')
    })
    .finally(() => {
      blueprintLoading.value = false
    })
}

function onOpenBlueprint(item: { id: string }) {
  router.push({ path: '/' + item.id })
}

function onDeleteBlueprint(item: { id: string }) {
  Modal.confirm({
    title: '删除确认',
    icon: createVNode(ExclamationCircleOutlined),
    content: createVNode('div', { style: 'color:red;' }, `确定要删除「${item.name || '未命名'}」吗？删除后不可恢复。`),
    okText: '确定删除',
    okType: 'danger',
    cancelText: '取消',
    onOk() {
      return apiBlueprintDelete({ id: item.id })
        .then(res => {
          if (res.code === 200) {
            window.dispatchEvent(new CustomEvent('blueprint:deleted', { detail: { id: item.id } }))
            message.success('已删除')
            loadBlueprints()
          } else {
            message.error(res.message || '删除失败')
          }
        })
        .catch(() => {
          message.error('删除失败，请重试')
        })
    },
  })
}

watch(
  () => tabsActiveKey.value,
  key => {
    if (key === '3') {
      selectedIds.value = new Set()
      if (blueprintList.value.length === 0) {
        loadBlueprints()
      }
    }
  },
)

function onBlueprintDeleted() {
  // refresh list if the blueprint tab has been loaded
  if (blueprintList.value.length > 0) {
    loadBlueprints()
  }
}

onMounted(() => {
  window.addEventListener('blueprint:deleted', onBlueprintDeleted)
})

onUnmounted(() => {
  window.removeEventListener('blueprint:deleted', onBlueprintDeleted)
})

handleGraphicGroups()
</script>

<style lang="less" scoped>
.graphics {
  height: calc(100vh - 50px);
  background: #fff;
  border-right: 1px solid #dddddd;
  z-index: 2;

  :deep(.ant-tabs) {
    .ant-tabs-nav {
      margin-bottom: 0;
    }

    .mkdir-head {
      margin: 12px;
      border-bottom: 1px solid #e5e5e5;
      box-sizing: border-box;

      .anticon {
        margin: 0 6px 0 0;
      }

      &:hover {
        color: #1890ff;
        cursor: pointer;
      }
    }
  }

  .scroll {
    height: calc(100vh - 199px);
    overflow-y: auto;
    // &::-webkit-scrollbar {
    //   width: 8px;
    //   height: 10px;
    //   background: transparent;
    // }
    // &::-webkit-scrollbar-thumb {
    //   background-color: #ddd;
    //   border-radius: 4px;
    // }
  }

  .more-graphical {
    height: 54px;
    border-top: 1px solid #e5e5e5;
    box-sizing: border-box;
  }

  .bp-toolbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 6px 8px;
    border-bottom: 1px solid #f0f0f0;
  }

  .blueprint-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 8px;
    padding: 8px;
    max-height: calc(100vh - 88px);
    overflow-y: auto;
    align-content: start;
  }

  .bp-card {
    border: 1px solid #f0f0f0;
    border-radius: 6px;
    overflow: hidden;
    transition: box-shadow 0.2s;
    position: relative;
    &:hover {
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
      border-color: #d9d9d9;
    }
  }

  .bp-card-selected {
    border-color: #4f46e5;
    box-shadow: 0 0 0 2px rgba(79, 70, 229, 0.15);
  }

  .bp-check {
    position: absolute;
    top: 4px;
    left: 4px;
    z-index: 2;
    background: rgba(255, 255, 255, 0.9);
    border-radius: 3px;
    padding: 1px;
  }

  .bp-card-body {
    cursor: pointer;
  }

  .bp-thumb {
    position: relative;
    height: 80px;
    background: #fafafa;
    overflow: hidden;
    display: flex;
    align-items: center;
    justify-content: center;
    img {
      width: 100%;
      height: 100%;
      object-fit: cover;
    }
  }

  .bp-placeholder-icon {
    color: #d9d9d9;
  }

  .bp-name {
    padding: 4px 6px 0;
    font-size: 12px;
    font-weight: 500;
    color: #333;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .bp-time {
    padding: 2px 6px 6px;
    font-size: 10px;
    color: #999;
  }

  .bp-card-actions {
    position: absolute;
    top: 2px;
    right: 2px;
  }

  .bp-delete-btn {
    font-size: 14px;
    color: #ff4d4f;
    cursor: pointer;
    padding: 2px;
    border-radius: 4px;
    &:hover {
      background: rgba(255, 77, 79, 0.1);
    }
  }
  :deep(.ant-collapse) {
    border-top: none;
    .ant-collapse-item {
      .ant-collapse-header {
        span {
        }
        .group-name {
          display: inline-block;
          max-width: 95px;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }
        .group-total {
          flex: 1;
        }
      }
    }
    .ant-collapse-content-box {
      padding: 3px;
      ul {
        padding: 0;
        margin: 0;
        list-style: none;
        .graphic {
          position: relative;
          width: 25%;
          height: 25%;
          padding: 6px;
          border-radius: 2px;
          border: 1px solid transparent;
          box-sizing: border-box;
          img {
            display: block;
            margin: 0 auto;
            max-width: 100px;
            max-height: 25px;
          }
          .iconfont {
            display: block;
            font-size: 28px;
            text-align: center;
          }

          &:hover {
            cursor: pointer;
            border-color: var(--color-primary);
          }

          p {
            display: -webkit-box;
            margin-top: 6px;
            padding: 0 8px;
            text-align: center;
            font-size: 12px;
            height: 12px;
            line-height: 1;
            overflow: hidden;
            text-overflow: ellipsis;
            -webkit-line-clamp: 1;
            word-break: break-all;
            -webkit-box-orient: vertical;
          }

          .t-icon {
            font-size: 26px;
          }

          .l-icon {
            height: 28px;
            width: 100%;
            margin: auto;
            color: var(--color);
          }
        }
      }
    }
  }
}
</style>
