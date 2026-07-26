<!--
 * @Descripttion:
 * @version: 1.0.0
 * @Author: htang
 * @Date: 2024-09-24 16:38:51
 * @LastEditors: htang
 * @LastEditTime: 2025-08-22 16:37:21
-->
<template>
  <a-modal
    v-model:visible="visible"
    title="资源文件管理器"
    width="1240px"
    centered
    :bodyStyle="bodyStyle"
    :destroyOnClose="true"
    :footer="footer"
    wrapClassName="file-manager-modal"
    @ok="handleOk"
  >
    <a-spin tip="素材加载中..." :spinning="spinning">
      <div class="file-manager flex justify-between flex-wrap">
        <div class="c-left">
          <div class="folder-tree">
            <template v-if="folderTreeData.length !== 0">
              <a-tree
                v-model:selectedKeys="selectedKeys"
                :tree-data="folderTreeData"
                default-expand-all
                show-icon
                :blockNode="true"
                @select="selectDirData"
              >
                <template #title="{ key: treeKey, title }">
                  <a-dropdown :trigger="['contextmenu']">
                    <span>{{ title }}</span>
                    <template #overlay>
                      <a-menu @click="({ key: menuKey }) => onContextMenuClick(treeKey, menuKey)">
                        <a-menu-item key="1">
                          <delete-outlined />
                          <span>删除</span>
                        </a-menu-item>
                      </a-menu>
                    </template>
                  </a-dropdown>
                </template>
                <template #icon="{ expanded }">
                  <FolderOpenOutlined v-if="expanded" />
                  <FolderOutlined v-else />
                </template>
              </a-tree>
            </template>
            <template v-else>
              <a-empty :image="simpleImage" description="暂无目录数据" />
            </template>
          </div>
          <div class="upload-item w-full pl-2 pr-2">
            <FileUpload ref="fileUploadRef" @oks="uploadSuccessDone" />
          </div>
        </div>
        <div class="file-container p-2" id="file-container">
          <div class="file-head flex items-center flex-wrap">
            <div class="operation-bar flex items-center w-full justify-between">
              <ul class="opt-list flex items-center">
                <li
                  title="返回"
                  class="opt-item icon ico-left"
                  :class="[historyIndex <= 0 ? 'disabled' : '']"
                  @click="goBack"
                ></li>
                <li
                  title="前进"
                  class="opt-item icon ico-right"
                  :class="[historyIndex >= historyStack.length - 1 ? 'disabled' : '']"
                  @click="goForward"
                ></li>
                <li class="opt-item liider"></li>
                <li
                  title="剪切"
                  class="opt-item icon ico-scissors"
                  :class="[actionIndex == -1 || spinning ? 'disabled' : '']"
                  @click="onCut"
                ></li>
                <li
                  title="复制"
                  class="opt-item icon ico-copy"
                  :class="[actionIndex == -1 || spinning ? 'disabled' : '']"
                  @click="onCopy"
                ></li>
                <li
                  title="黏贴"
                  class="opt-item icon ico-paste"
                  :class="[!clipboard || spinning ? 'disabled' : '']"
                  @click="onPaste"
                >
                  <span v-if="clipboard" class="clipboard-badge">{{ clipboard.action === 'cut' ? '✂' : '📋' }}</span>
                </li>
                <li
                  title="重命名"
                  class="opt-item icon ico-rename"
                  :class="[actionIndex == -1 || spinning ? 'disabled' : '']"
                  @click="onModifyRename"
                ></li>
                <li
                  title="删除"
                  class="opt-item icon ico-trash"
                  :class="[selectedRowKeys.length == 0 || spinning ? 'disabled' : '']"
                  @click="onDelete"
                ></li>
                <li class="opt-item liider"></li>
                <li title="新建目录" class="opt-item icon ico-add-dir" @click="onCreateDirectory"></li>
                <li
                  title="全选"
                  class="opt-item icon ico-select-all"
                  :class="[mode == 'single' ? 'disabled' : '']"
                  @click="onSelectAll"
                ></li>
                <li
                  title="切换布局"
                  class="opt-item icon ico-list-layout"
                  :class="[currentLayout == 'list' ? 'ico-list-layout' : 'ico-grid-layout']"
                  @click="onToggleLayouts"
                ></li>
                <li title="同步文件" class="opt-item icon ico-refresh" @click="onRefresh()"></li>
              </ul>
              <a-form layout="inline">
                <a-form-item>
                  <a-input
                    v-model:value="queryParam.keyword"
                    placeholder="请输入关键字搜索"
                    @keydown.enter="onSearch"
                    allowClear
                  >
                    <template #prefix>
                      <SearchOutlined />
                    </template>
                  </a-input>
                </a-form-item>
              </a-form>
            </div>
            <div class="crumb-sort-bar flex items-center justify-between w-full">
              <a-breadcrumb>
                <a-breadcrumb-item @click="navigateToPathSegment(-1)" style="cursor: pointer">
                  <home-outlined />
                </a-breadcrumb-item>
                <template v-for="(item, idx) in currentPath" :key="idx">
                  <template v-if="idx < currentPath.length - 1">
                    <a-breadcrumb-item @click="navigateToPathSegment(idx)" style="cursor: pointer">
                      {{ item }}
                    </a-breadcrumb-item>
                  </template>
                  <template v-else>
                    <a-breadcrumb-item>
                      {{ item }}
                    </a-breadcrumb-item>
                  </template>
                </template>
              </a-breadcrumb>
              <div class="sort flex items-center">
                <span title="切换排序类型" class="sort-item sort-date"> 时间排序 </span>
                <i
                  title="切换排序次序"
                  class="sort-item icon ml-1"
                  :class="[queryParam.sort_order == 'DESC' ? 'ico-down' : 'ico-up']"
                  @click="onSort()"
                ></i>
              </div>
            </div>
          </div>
          <template v-if="dataSource.length !== 0">
            <div class="file-list" :class="[currentLayout == 'grid' ? 'layout-grid' : 'layout-list']">
              <template v-for="(item, idx) in dataSource" :key="idx">
                <div
                  class="file-item"
                  :class="[actionIndex == idx || selectedRowKeys.includes(item.id) ? 'selected' : '']"
                  @click="onSelectFile(item, idx)"
                  @dblclick="onOperateFileOrDir(item)"
                >
                  <template v-if="mode == 'multiple'">
                    <div class="checkbox-wrap" @click.native.stop="onMultipleChoices(item, idx)">
                      <div class="icon ico-checkbox"></div>
                    </div>
                  </template>
                  <div class="bg-thumb" :style="{ backgroundImage: formatBackgroundImage(item) }"></div>
                  <div class="title">{{ item.name }}</div>
                  <template v-if="item.type !== 'dir'">
                    <div class="preview">
                      <span>预览</span>
                    </div>
                  </template>
                  <div class="icon" :class="[item.lock == 1 ? 'ico-lock-on-face' : '']"></div>
                  <div class="date">{{ item.created_at }}</div>
                </div>
              </template>
            </div>
            <div class="table-footer flex items-center justify-end">
              <a-pagination
                v-model:current="ipagination.current"
                :total="ipagination.total"
                show-less-items
                show-quick-jumper
                @change="onChangePagination"
              />
            </div>
          </template>
          <template v-else>
            <a-empty :image="simpleImage" description="暂无文件数据" />
          </template>
        </div>
      </div>
    </a-spin>
    <FilePreview ref="filePreviewRef" />
    <Rename ref="renameRef" @success="init()" />
  </a-modal>
</template>

<script lang="ts" setup>
import { ref, createVNode, watch, nextTick, computed, onUnmounted } from 'vue'
import {
  apiMaterialList,
  apiMaterialFolder,
  apiMaterialDelete,
  apiMaterialCreatedFolder,
  apiMaterialCopy,
  apiMaterialScissors,
} from '@/api/material'
import { FileUpload, FilePreview, Rename } from './components/index'
import { getFileIconByExt } from './config.ts'
import { Modal, Empty, message } from 'ant-design-vue'
import {
  FolderOutlined,
  FolderOpenOutlined,
  ExclamationCircleOutlined,
  DeleteOutlined,
  HomeOutlined,
  SearchOutlined,
} from '@ant-design/icons-vue'

const fileUploadRef = ref(null)
const filePreviewRef = ref(null)
const renameRef = ref(null)

const props = defineProps({
  mode: {
    type: String,
    default: 'single', // single: 单选, multiple: 多选, view 查看
  },
})

const fileUpload = ref(null)

const simpleImage = Empty.PRESENTED_IMAGE_SIMPLE

const emit = defineEmits(['oks'])

const currentPath = ref([])

const bodyStyle = ref({
  padding: '0',
})

const mode = ref(props.mode)

// 剪贴板：{ data, action: 'copy' | 'cut' }
const clipboard = ref<{ data: any; action: 'copy' | 'cut' } | null>(null)

const footer = computed(() => {
  if (mode.value === 'view') {
    return null
  }
  return undefined
})

const actionIndex = ref(-1)

const queryParam = ref({
  keyword: '',
  type: '',
  parent_id: '',
  sort_order: 'DESC',
})

const selectedKeys = ref([])

const currentLayout = ref('grid')

const spinning = ref(false)

const visible = ref(false)

const selectedRowKeys = ref([])

const ipagination = ref({
  current: 1,
  pageSize: 10,
  pageSizeOptions: ['10', '20', '30'],
  showTotal: (total, range) => {
    return range[0] + '-' + range[1] + ' 共' + total + '条'
  },
  showQuickJumper: true,
  showSizeChanger: true,
  total: 0,
})

const dataSource = ref([])

const folderTreeData = ref([])

// 导航历史
interface HistoryEntry {
  parent_id: string
  currentPath: string[]
  selectedKeys: (string | number)[]
  selectedRowKeys: (string | number)[]
}
const historyStack = ref<HistoryEntry[]>([])
const historyIndex = ref(-1)
let isNavigating = false

function pushHistory() {
  if (isNavigating) return
  // Skip duplicate consecutive entries
  const last = historyStack.value[historyIndex.value]
  if (last && last.parent_id === queryParam.value.parent_id) return
  const entry: HistoryEntry = {
    parent_id: queryParam.value.parent_id,
    currentPath: [...currentPath.value],
    selectedKeys: [...selectedKeys.value],
    selectedRowKeys: [...selectedRowKeys.value],
  }
  // Truncate forward history if we're not at the tip
  if (historyIndex.value < historyStack.value.length - 1) {
    historyStack.value = historyStack.value.slice(0, historyIndex.value + 1)
  }
  historyStack.value.push(entry)
  historyIndex.value = historyStack.value.length - 1
}

function goBack() {
  if (historyIndex.value <= 0) return
  historyIndex.value--
  applyHistoryEntry(historyStack.value[historyIndex.value])
}

function goForward() {
  if (historyIndex.value >= historyStack.value.length - 1) return
  historyIndex.value++
  applyHistoryEntry(historyStack.value[historyIndex.value])
}

function applyHistoryEntry(entry: HistoryEntry) {
  isNavigating = true
  queryParam.value.parent_id = entry.parent_id
  currentPath.value = entry.currentPath
  selectedKeys.value = entry.selectedKeys
  selectedRowKeys.value = entry.selectedRowKeys
  actionIndex.value = -1
  init()
  nextTick(() => {
    isNavigating = false
  })
}

// Track pending image loads so they can be cancelled on unmount / re-init
let pendingImages: HTMLImageElement[] = []

/**
 * 初始化资源文件
 */
async function init() {
  spinning.value = true
  // Cancel any in-flight image onload handlers from previous init
  pendingImages.forEach(img => {
    img.onload = null
  })
  pendingImages = []

  let { current, pageSize } = ipagination.value
  let data: Record<string, any> = {
    current,
    page_size: pageSize,
  }
  for (const [key, val] of Object.entries(queryParam.value)) {
    if (val !== '') {
      data[key] = val
    }
  }
  await apiMaterialList(data)
    .then(res => {
      spinning.value = false
      if (res.data) {
        let { list, current, page_size, total } = res.data
        dataSource.value = list.map((_: any) => {
          if (['jpg', 'png', 'jpeg', 'gif'].includes(_.extension)) {
            const img = new Image()
            pendingImages.push(img)
            img.onload = () => {
              _['width'] = img.width
              _['height'] = img.height
            }
            img.src = _.url
          }
          return _
        })
        Object.assign(ipagination.value, {
          current,
          pageSize: page_size,
          total,
        })
      }
    })
    .catch(() => {
      spinning.value = false
      message.error('加载文件列表失败')
    })
}

function selectDirData(e, { node }) {
  let [a] = e
  pushHistory()
  currentPath.value = node.path.split('/')
  actionIndex.value = -1
  selectedRowKeys.value = []
  const parentId = e.length !== 0 ? a : ''
  queryParam.value.parent_id = parentId
  if (fileUploadRef.value) {
    Object.assign(fileUploadRef.value.data, { parent_id: parentId })
  }
  init()
}

/**
 * 面包屑点击导航：根据路径深度找到对应层级的文件夹节点并打开
 * @param {Number} idx - 路径段索引，-1 表示根目录
 */
function navigateToPathSegment(idx: number) {
  pushHistory()
  actionIndex.value = -1
  selectedRowKeys.value = []
  if (idx < 0) {
    // 回到根目录
    queryParam.value.parent_id = ''
    selectedKeys.value = []
    currentPath.value = []
    init()
    return
  }
  const segments = currentPath.value.slice(0, idx + 1)
  const targetPath = segments.join('/')
  const foundNode = findNodeByPath(folderTreeData.value, targetPath)
  if (foundNode) {
    queryParam.value.parent_id = foundNode.id
    selectedKeys.value = [foundNode.id]
    currentPath.value = foundNode.path.split('/')
    init()
  }
}

/**
 * 在文件夹树中按路径查找节点
 */
function findNodeByPath(tree: any[], path: string): any {
  for (const node of tree) {
    if (node.path === path) return node
    if (node.children) {
      const found = findNodeByPath(node.children, path)
      if (found) return found
    }
  }
  return null
}

const onSearch = () => init()

/**
 * 初始化文件目录数据
 */
async function initMaterialFolder() {
  const request = await apiMaterialFolder({}).catch(() => {
    message.error('加载文件夹失败')
    return { data: null }
  })
  if (request.data) {
    folderTreeData.value = mapDataToTree(request.data)
  }
}

const mapDataToTree = data => {
  return data.map(item => ({
    ...item,
    key: item.id,
    title: item.name,
    children: item.children ? mapDataToTree(item.children) : null,
  }))
}

/**
 * 打开文件夹
 */
function openFolder(e) {
  if (e.type == 'dir') {
    pushHistory()
    queryParam.value.parent_id = e.id
    actionIndex.value = -1
    selectedRowKeys.value = []
    selectedKeys.value = [e.id]
    init()
  }
}

const onContextMenuClick = (treeKey: string, menuKey: string | number) => {
  apiMaterialDelete({ id: treeKey })
    .then(res => {
      message.success('删除成功')
      initMaterialFolder()
    })
    .catch(() => {
      message.error('删除失败')
    })
}

/**
 * 删除素材文件
 * @param {Number} id 素材ID
 */
function onDelete() {
  Modal.confirm({
    title: '删除提示',
    icon: createVNode(ExclamationCircleOutlined),
    content: '确认删除选中的文件夹? 请谨慎删除。',
    okText: '确认',
    cancelText: '取消',
    okType: 'danger',
    onOk() {
      const promises = selectedRowKeys.value.map((id: string) => apiMaterialDelete({ id }))
      Promise.all(promises).then(() => {
        message.success('删除成功')
        init()
        initMaterialFolder()
      })
    },
  })
}

const onSelectAll = () => {
  if (mode.value == 'multiple') {
    if (selectedRowKeys.value.length == dataSource.value.length) {
      selectedRowKeys.value = []
    } else {
      selectedRowKeys.value = dataSource.value.map(k => k.id)
    }
  }
}

/**
 * 上传文件回调
 */
const uploadSuccessDone = () => init()

function onChangePagination(e) {
  ipagination.value.current = e
  init()
}

const onToggleLayouts = () => {
  currentLayout.value == 'list' ? (currentLayout.value = 'grid') : (currentLayout.value = 'list')
}

/**
 * 新建目录
 */
const onCreateDirectory = () => {
  let data = {}
  let { parent_id } = queryParam.value
  if (parent_id) {
    data['parent_id'] = parent_id
  }
  apiMaterialCreatedFolder(data)
    .then(res => {
      message.success((res as any).message)
      init()
      initMaterialFolder()
    })
    .catch(() => {
      message.error('创建目录失败')
    })
}

const onOperateFileOrDir = (params: any) => {
  if (params.type == 'dir') {
    openFolder(params)
  } else {
    switch (params.extension) {
      case 'png':
      case 'jpg':
      case 'jpeg':
      case 'gif':
      case 'svg':
        {
          const img = new Image()
          img.onload = () => {
            img.onload = null
            filePreviewRef.value?.openPreview({
              url: params.url,
              width: img.width,
              height: img.height,
            })
          }
          img.src = params.url
        }
        break
      case 'md':
      case 'markdown':
        fetch(params.url)
          .then(res => res.text())
          .then(text => {
            filePreviewRef.value.openTextPreview({
              content: text,
              type: 'markdown',
              title: params.name,
            })
          })
          .catch(() => message.error('加载文件失败'))
        break
      case 'json':
      case 'js':
      case 'ts':
      case 'css':
      case 'html':
      case 'xml':
      case 'yaml':
      case 'yml':
      case 'py':
      case 'sh':
      case 'sql':
      case 'csv':
      case 'txt':
      case 'log':
      case 'ini':
      case 'cfg':
      case 'conf':
        fetch(params.url)
          .then(res => res.text())
          .then(text => {
            filePreviewRef.value.openTextPreview({
              content: text,
              type: params.extension,
              title: params.name,
            })
          })
          .catch(() => message.error('加载文件失败'))
        break
      default:
        // Try as plain text, fallback to opening in new tab
        fetch(params.url)
          .then(res => res.text())
          .then(text => {
            filePreviewRef.value.openTextPreview({
              content: text,
              type: 'text',
              title: params.name,
            })
          })
          .catch(() => {
            window.open(params.url, '_blank')
          })
        break
    }
  }
}

const formatBackgroundImage = (params: any) => {
  return getFileIconByExt(params.extension || params.type)
}

const onSelectFile = (params: any, idx: any) => {
  if (actionIndex.value == idx) {
    actionIndex.value = -1
    return false
  }
  actionIndex.value = idx
}

const onMultipleChoices = ({ id }, idx: number) => {
  if (selectedRowKeys.value.includes(id)) {
    selectedRowKeys.value.splice(selectedRowKeys.value.indexOf(id), 1)
  } else {
    selectedRowKeys.value.push(id)
  }
}

/**
 * 刷新文件列表
 */
const onRefresh = () => init()

function handleKeydown(e: KeyboardEvent) {
  // Don't capture shortcuts when focus is in an input
  const tag = (e.target as HTMLElement)?.tagName
  if (['INPUT', 'TEXTAREA', 'SELECT'].includes(tag)) return

  if (e.key === 'Delete') {
    if (selectedRowKeys.value.length > 0) onDelete()
  } else if (e.key === 'F2') {
    e.preventDefault()
    onModifyRename()
  } else if (e.ctrlKey && e.key === 'c') {
    e.preventDefault()
    onCopy()
  } else if (e.ctrlKey && e.key === 'x') {
    e.preventDefault()
    onCut()
  } else if (e.ctrlKey && e.key === 'v') {
    e.preventDefault()
    onPaste()
  }
}

watch(
  () => visible.value,
  val => {
    selectedRowKeys.value = []
    actionIndex.value = -1
    if (val) {
      // Reset navigation history when modal opens
      historyStack.value = []
      historyIndex.value = -1
      document.addEventListener('keydown', handleKeydown)
    } else {
      folderTreeData.value = []
      dataSource.value = []
      queryParam.value = {
        keyword: '',
        type: '',
        parent_id: '',
        sort_order: 'DESC',
      }
      document.removeEventListener('keydown', handleKeydown)
    }
  },
)

watch(
  () => queryParam.value.type,
  e => {
    if (fileUpload.value) {
      fileUpload.value.typeValue = e || ''
    }
  },
)

watch(
  () => queryParam.value.parent_id,
  parent_id => {
    if (parent_id && fileUploadRef.value) {
      Object.assign(fileUploadRef.value.data, {
        parent_id,
      })
    }
  },
)

const onSort = () => {
  let { sort_order } = queryParam.value
  sort_order == 'DESC' ? (queryParam.value.sort_order = 'ASC') : (queryParam.value.sort_order = 'DESC')
  init()
}

const onModifyRename = () => {
  const item = dataSource.value[actionIndex.value]
  if (!item) return
  renameRef.value.visible = true
  nextTick(() => {
    renameRef.value.init({ id: item.id, name: item.name })
  })
}

const onCopy = () => {
  const data = dataSource.value[actionIndex.value]
  if (!data) return
  clipboard.value = { data, action: 'copy' }
  message.success(`已复制「${data.name}」`)
}

const onCut = () => {
  const data = dataSource.value[actionIndex.value]
  if (!data) return
  clipboard.value = { data, action: 'cut' }
  message.success(`已剪切「${data.name}」`)
}

const onPaste = () => {
  if (!clipboard.value) return
  const { data, action } = clipboard.value
  spinning.value = true
  const apiFn = action === 'cut' ? apiMaterialScissors : apiMaterialCopy
  apiFn({ id: data.id, folder: queryParam.value.parent_id })
    .then(res => {
      spinning.value = false
      clipboard.value = null
      actionIndex.value = -1
      init()
      if (action === 'cut') initMaterialFolder()
      message.success('粘贴成功')
    })
    .catch(() => {
      spinning.value = false
      clipboard.value = null
      message.error('粘贴失败')
    })
}

const handleOk = () => {
  switch (mode.value) {
    case 'multiple':
      let fileList: any = []
      dataSource.value.map((k: any) => {
        if (selectedRowKeys.value.includes(k.id)) {
          fileList.push(k)
        }
      })
      emit('oks', fileList)
      break
    case 'single':
      if (actionIndex.value !== -1) {
        emit('oks', dataSource.value[actionIndex.value])
      }
      break
  }
  visible.value = false
}

onUnmounted(() => {
  pendingImages.forEach(img => {
    img.onload = null
  })
  pendingImages = []
  document.removeEventListener('keydown', handleKeydown)
})

defineExpose({
  selectedKeys,
  queryParam,
  visible,
  init,
  initMaterialFolder,
})
</script>

<style lang="less" scoped>
.file-manager-modal {
  .file-manager {
    background: #f2f4f8;

    .c-left {
      width: 212px;
      height: inherit;

      .folder-tree {
        width: 100%;
        height: calc(100% - 44px);
        padding: 6px 0;
        overflow: hidden;
        overflow-y: scroll;

        &::-webkit-scrollbar {
          width: 8px;
          height: 4px;
        }

        &::-webkit-scrollbar-thumb {
          width: 5px;
          height: 5px;
          background-color: #bdbdbd;
        }

        &::-webkit-scrollbar,
        &::-webkit-scrollbar-track {
          background-color: #f5f5f5;
        }

        :deep(.ant-tree-iconEle) {
          line-height: 17px;
        }

        :deep(.ant-tree) {
          background: transparent;

          .ant-tree-node-content-wrapper {
            overflow: hidden;
            white-space: nowrap;
            text-overflow: ellipsis;
          }
        }
      }

      .upload-item {
        height: 44px;
        background: #f1f1f1;
      }
    }

    .file-container {
      width: calc(100% - 212px);
      height: 50vh;
      min-height: 500px;
      background: #fff;
      border-left: 1px solid #d9d9d9;
      box-sizing: border-box;

      .file-head {
        width: 100%;

        .operation-bar {
          height: 48px;

          .opt-list {
            padding: 0;
            margin: 0;

            .opt-item {
              display: block;
              width: 32px;
              height: 32px;
              margin-left: 8px;
              border-radius: 4px;
              cursor: pointer;

              &:first-child {
                margin: 0;
              }

              &:hover {
                background: #e0e0e0;
              }

              &.liider {
                width: 1px;
                margin: 0 0 0 8px;
                border: none;
                background: #e0e0e0;
              }

              &.icon {
                background-position: 50%;
                background-size: 24px;
                background-repeat: no-repeat;
                background-position: center;

                &.disabled {
                  cursor: not-allowed;
                }

                &.ico-left {
                  background-image: url('@/assets/images/file-explorer/icon/左2.svg');

                  &.disabled {
                    background-image: url('@/assets/images/file-explorer/icon/左2浅灰.svg');
                  }
                }

                &.ico-right {
                  background-image: url('@/assets/images/file-explorer/icon/右2.svg');

                  &.disabled {
                    background-image: url('@/assets/images/file-explorer/icon/右2浅灰.svg');
                  }
                }

                &.ico-edit {
                  background-image: url('@/assets/images/file-explorer/icon/edit_gray_linear.svg');

                  &.disabled {
                    background-image: url('@/assets/images/file-explorer/icon/edit_light_gray_linear.svg');
                  }
                }

                &.ico-scissors {
                  background-image: url('@/assets/images/file-explorer/icon/剪刀.svg');

                  &.disabled {
                    background-image: url('@/assets/images/file-explorer/icon/剪刀浅灰.svg');
                  }
                }

                &.ico-copy {
                  background-image: url('@/assets/images/file-explorer/icon/复制.svg');

                  &.disabled {
                    background-image: url('@/assets/images/file-explorer/icon/复制浅灰.svg');
                  }
                }

                &.ico-paste {
                  background-image: url('@/assets/images/file-explorer/icon/粘帖.svg');
                  position: relative;

                  &.disabled {
                    background-image: url('@/assets/images/file-explorer/icon/粘帖浅灰.svg');
                  }

                  .clipboard-badge {
                    position: absolute;
                    top: -4px;
                    right: -4px;
                    font-size: 10px;
                    line-height: 1;
                    pointer-events: none;
                  }
                }

                &.ico-rename {
                  background-image: url('@/assets/images/file-explorer/icon/重命名.svg');

                  &.disabled {
                    background-image: url('@/assets/images/file-explorer/icon/重命名浅灰.svg');
                  }
                }

                &.ico-trash {
                  background-image: url('@/assets/images/file-explorer/icon/垃圾桶.svg');

                  &.disabled {
                    background-image: url('@/assets/images/file-explorer/icon/垃圾桶浅灰.svg');
                  }
                }

                &.ico-lock-on {
                  background-image: url('@/assets/images/file-explorer/icon/lock_on_deep_gray_linear.svg');

                  &.disabled {
                    background-image: url('@/assets/images/file-explorer/icon/lock_on_gray_linear2.svg');
                  }
                }

                &.ico-add-dir {
                  background-image: url('@/assets/images/file-explorer/icon/创建文件夹.svg');
                }

                &.ico-select-all {
                  background-image: url('@/assets/images/file-explorer/icon/全选.svg');
                }

                &.ico-list-layout {
                  background-image: url('@/assets/images/file-explorer/icon/列表.svg');
                }

                &.ico-grid-layout {
                  background-image: url('@/assets/images/file-explorer/icon/网格.svg');
                }

                &.ico-refresh {
                  background-image: url('@/assets/images/file-explorer/icon/refresh_gray_linear.svg');
                }
              }
            }
          }

          .ant-form {
            .ant-form-item {
              &:last-child {
                margin: 0;
              }
            }
          }
        }

        .crumb-sort-bar {
          height: 24px;
          margin: 0 0 6px;

          :deep(.ant-breadcrumb .anticon) {
            position: relative;
            top: -3px;
          }

          .sort {
            .icon {
              display: block;
              height: 24px;
              width: 24px;
              border-radius: 4px;
              background-repeat: no-repeat;
              background-position: center;
              cursor: pointer;

              &:hover {
                background-color: #e0e0e0;
              }

              &.ico-up {
                background-image: url('@/assets/images/file-explorer/icon/上2.svg');
              }

              &.ico-down {
                background-image: url('@/assets/images/file-explorer/icon/下2.svg');
              }
            }
          }
        }
      }

      .file-list {
        padding: 8px;
        margin: 0 0 12px;
        grid-gap: 8px;

        .file-item {
          .checkbox-wrap {
            position: absolute;
            top: -1px;
            left: -1px;
            display: none;
            padding: 1px;
            border: 1px solid #18bc9c;
            border-radius: 4px 0;
            line-height: 0;
            background: #fff;
            cursor: pointer;

            .ico-checkbox {
              height: 24px;
              width: 24px;
              background-size: 24px;
            }
          }

          .ico-lock-on-face {
            height: 16px;
            width: 16px;
            background-size: 16px;
            background-repeat: no-repeat;
            background-image: url('@/assets/images/file-explorer/icon/lock_on_face.svg');
          }

          &:hover {
            .checkbox-wrap {
              .ico-checkbox {
                background-image: url('@/assets/images/file-explorer/icon/checkbox_gray_linear.svg');
              }
            }
          }

          &.selected {
            .checkbox-wrap {
              .ico-checkbox {
                background-image: url('@/assets/images/file-explorer/icon/checkbox_checked_face.svg');
              }
            }
          }
        }

        &.layout-grid,
        &.layout-list {
          height: calc(100% - 136px);
          overflow: hidden;
          overflow-y: scroll;

          &::-webkit-scrollbar {
            width: 8px;
            height: 4px;
          }

          &::-webkit-scrollbar-thumb {
            width: 5px;
            height: 5px;
            background-color: #bdbdbd;
          }

          &::-webkit-scrollbar,
          &::-webkit-scrollbar-track {
            background-color: #f5f5f5;
          }
        }

        &.layout-grid {
          display: grid;
          margin: 0 0 12px;
          grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
          grid-auto-rows: 144px;

          .file-item {
            position: relative;
            background-color: #fff;
            border: 1px solid #e0e0e0;
            border-radius: 4px;
            text-align: center;
            overflow: hidden;
            transition: border-color 0.3s;
            cursor: pointer;

            .preview {
              position: absolute;
              bottom: 31px;
              left: 0;
              display: none;
              width: 100%;
              height: 30px;
              background: #18bc9c;
              border-radius: 5px 5px 0 0;
              line-height: 31px;
              span {
                color: #fff;
              }
            }

            .bg-thumb {
              height: 112px;
              border-bottom: 1px solid #e0e0e0;
              box-sizing: border-box;
              background-position: 50%;
              background-size: 85%;
              background-repeat: no-repeat;
            }

            .ico-lock-on-face {
              position: absolute;
              top: 94px;
              right: 2px;
            }

            .title {
              padding: 6px 8px;
              font-size: 12px;
              line-height: 20px;
              font-weight: 400;
              background-color: initial;
              white-space: nowrap;
              overflow: hidden;
              text-overflow: ellipsis;
            }

            &:hover {
              border-color: #18bc9c;

              .preview {
                display: block;
              }

              .checkbox-wrap {
                display: block;

                .ico-checkbox {
                  background-image: url('@/assets/images/file-explorer/icon/checkbox_gray_linear.svg');
                }
              }
            }

            &.selected {
              cursor: default;

              .checkbox-wrap {
                display: block;

                .ico-checkbox {
                  background-image: url('@/assets/images/file-explorer/icon/checkbox_checked_face.svg');
                }
              }

              .title {
                background-color: #dcf5f0;
                font-weight: 600;
                color: #18bc9c;
              }
            }
          }
        }

        &.layout-list {
          .file-item {
            position: relative;
            display: flex;
            padding: 8px;
            border-radius: 4px;
            border: 1px solid transparent;
            box-sizing: border-box;
            align-items: center;
            cursor: pointer;

            .preview {
              font-size: 12px;
            }

            .checkbox-wrap {
              .ico-checkbox {
                height: 24px;
                width: 24px;
                background-size: 24px;
              }
            }

            &:hover,
            &.selected {
              .checkbox-wrap {
                display: block;
                top: 7px;
                left: 7px;
                border: none;
              }
            }

            &:hover {
              background: #fff;
              border-color: #18bc9c;

              &:nth-child(even) {
                background-color: #fff;
              }
            }

            &.selected {
              background-color: #dcf5f0;
            }

            &:nth-child(even) {
              background-color: #f5f5f5;
            }

            .bg-thumb {
              height: 24px;
              width: 24px;
              border-radius: 2px;
              box-sizing: border-box;
              background-size: cover;
              background-position: 50%;
              background-repeat: no-repeat;
            }

            .title {
              padding: 0 8px;
              text-align: left;
              overflow: hidden;
              text-overflow: ellipsis;
              white-space: nowrap;
              flex: 1;
            }

            .date {
              padding-left: 8px;
              margin-left: 8px;
              flex: 0 0 168px;
              color: #7a7a7a;
            }
          }
        }
      }

      .table-footer {
        margin: 0 12px;

        .ant-pagination {
          text-align: right;
        }
      }
    }
  }
}
</style>

<style lang="less">
.ant-dropdown {
  .ant-dropdown-menu-title-content {
    display: flex;
    align-items: center;

    span {
      &:first-child {
        margin: 0 6px 0 0;
      }
    }
  }
}
</style>
