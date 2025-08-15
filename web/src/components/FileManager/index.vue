<!--
 * @Descripttion:
 * @version: 1.0.0
 * @Author: htang
 * @Date: 2024-09-24 16:38:51
 * @LastEditors: htang
 * @LastEditTime: 2025-08-15 11:04:38
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
                      <a-menu
                        @click="
                          ({ key: menuKey }) =>
                            onContextMenuClick(treeKey, menuKey)
                        "
                      >
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
          <div class="upload-item flex items-center justify-center">
            <FileUpload ref="fileUpload" @oks="uploadSuccessDone" />
          </div>
        </div>
        <div class="file-container p-2" id="file-container">
          <div class="file-head flex items-center flex-wrap">
            <div class="operation-bar flex items-center w-full justify-between">
              <ul class="opt-list flex items-center">
                <li title="返回" class="opt-item icon ico-left disabled"></li>
                <li title="前进" class="opt-item icon ico-right disabled"></li>
                <li class="opt-item liider"></li>
                <li title="编辑" class="opt-item icon ico-edit disabled"></li>
                <li
                  title="剪切"
                  class="opt-item icon ico-scissors"
                  :class="[
                    actionIndex == -1 || !isCopy || spinning ? 'disabled' : '',
                  ]"
                  @click="onScissors"
                ></li>
                <li
                  title="复制"
                  class="opt-item icon ico-copy"
                  :class="[
                    actionIndex == -1 || isCopy || spinning ? 'disabled' : '',
                  ]"
                  @click="onCopy"
                ></li>
                <li
                  title="黏贴"
                  class="opt-item icon ico-paste"
                  :class="[
                    actionIndex == -1 || !isCopy || spinning ? 'disabled' : '',
                  ]"
                  @click="onPaste"
                ></li>
                <li
                  title="重命名"
                  class="opt-item icon ico-rename"
                  :class="[actionIndex == -1 || spinning ? 'disabled' : '']"
                  @click="onModifyRename"
                ></li>
                <li
                  title="删除"
                  class="opt-item icon ico-trash"
                  :class="[
                    selectedRowKeys.length == 0 || spinning ? 'disabled' : '',
                  ]"
                  @click="onDelete"
                ></li>
                <li class="opt-item liider"></li>
                <li
                  title="锁定目录"
                  class="opt-item icon ico-lock-on"
                  :class="[isLock !== 1 || spinning ? 'disabled' : '']"
                ></li>
                <li
                  title="新建目录"
                  class="opt-item icon ico-add-dir"
                  @click="onCreateDirectory"
                ></li>
                <li
                  title="全选"
                  class="opt-item icon ico-select-all"
                  :class="[mode == 'single' ? 'disabled' : '']"
                  @click="onSelectAll"
                ></li>
                <li
                  title="切换布局"
                  class="opt-item icon ico-list-layout"
                  :class="[
                    currentLayout == 'list'
                      ? 'ico-list-layout'
                      : 'ico-grid-layout',
                  ]"
                  @click="onToggleLayouts"
                ></li>
                <li
                  title="同步文件"
                  class="opt-item icon ico-refresh"
                  @click="onRefresh()"
                ></li>
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
            <div
              class="crumb-sort-bar flex items-center justify-between w-full"
            >
              <a-breadcrumb>
                <a-breadcrumb-item>
                  <home-outlined />
                </a-breadcrumb-item>
                <template v-for="(item, idx) in currentPath" :key="idx">
                  <a-breadcrumb-item>
                    {{ item }}
                  </a-breadcrumb-item>
                </template>
              </a-breadcrumb>
              <div class="sort flex items-center">
                <span title="切换排序类型" class="sort-item sort-date">
                  时间排序
                </span>
                <i
                  title="切换排序次序"
                  class="sort-item icon ml-1"
                  :class="[
                    queryParam.sort_order == 'DESC' ? 'ico-down' : 'ico-up',
                  ]"
                  @click="onSort()"
                ></i>
              </div>
            </div>
          </div>
          <template v-if="dataSource.length !== 0">
            <div
              class="file-list"
              :class="[currentLayout == 'grid' ? 'layout-grid' : 'layout-list']"
            >
              <template v-for="(item, idx) in dataSource" :key="idx">
                <div
                  class="file-item fi-dir"
                  :class="[
                    actionIndex == idx || selectedRowKeys.includes(item.id)
                      ? 'selected'
                      : '',
                  ]"
                  @dblclick="onOperateFileOrDir(item)"
                  @click="onSelectFile(item, idx)"
                >
                  <template v-if="mode == 'multiple'">
                    <div
                      class="checkbox-wrap"
                      @click.native.stop="onMultipleChoices(item, idx)"
                    >
                      <div class="icon ico-checkbox"></div>
                    </div>
                  </template>
                  <div
                    class="bg-thumb"
                    :style="{ backgroundImage: formatBackgroundImage(item) }"
                  ></div>
                  <div class="title">{{ item.name }}</div>
                  <div
                    class="icon"
                    :class="[item.lock == 1 ? 'ico-lock-on-face' : '']"
                  ></div>
                  <div class="date">{{ item.created_at }}</div>
                  <div class="size"></div>
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
    <FilePreview ref="filePreview" />
    <Rename ref="rename" @success="init()" />
  </a-modal>
</template>

<script lang="ts" setup>
import {
  ref,
  createVNode,
  getCurrentInstance,
  watch,
  nextTick,
  computed,
} from "vue";
import {
  apiMaterialList,
  apiMaterialFolder,
  apiMaterialDelete,
  apiMaterialCreatedFolder,
  apiMaterialCopy,
  apiMaterialScissors,
} from "@/api/material";
import { FileUpload, FilePreview, Rename } from "./components/index";
import { getFileIconByExt } from "./config.ts";
import { Modal, Empty, message } from "ant-design-vue";
import {
  FolderOutlined,
  FolderOpenOutlined,
  ExclamationCircleOutlined,
  DeleteOutlined,
  HomeOutlined,
  SearchOutlined,
} from "@ant-design/icons-vue";

const { proxy }: any = getCurrentInstance();

const props = defineProps({
  mode: {
    type: String,
    default: "single", // single: 单选, multiple: 多选, view 查看
  },
});

const fileUpload = ref(null);

const simpleImage = Empty.PRESENTED_IMAGE_SIMPLE;

const emit = defineEmits(["oks"]);

const currentPath = ref([]);

const bodyStyle = ref({
  padding: "0",
});

const sortType = ref("created_at");

const mode = ref(props.mode);

// 是否复制
const isCopy = ref(false);

const currentCopyData = ref({});

// 黏贴
const isPaste = ref(false);

// 剪切
const isScissors = ref(false);

const footer = computed(() => {
  if (mode.value == "view") {
    return null;
  }
});

const actionIndex = ref(-1);

let queryParam = ref({
  keyword: "",
  type: "",
  parent_id: "",
  sort_order: "DESC",
});

let tableContentHeight = ref(0);

let selectedKeys = ref([]);

let currentLayout = ref("grid");

let spinning = ref(false);

let visible = ref(false);

let selectedRowKeys = ref([]);

let ipagination = ref({
  current: 1,
  pageSize: 10,
  pageSizeOptions: ["10", "20", "30"],
  showTotal: (total, range) => {
    return range[0] + "-" + range[1] + " 共" + total + "条";
  },
  showQuickJumper: true,
  showSizeChanger: true,
  total: 0,
});

let dataSource = ref([]);

let folderTreeData = ref([]);

const isLock = computed(() => {
  let data = dataSource.value[actionIndex.value];
  if (data && selectedRowKeys.value.length <= 1) {
    return data.lock == 1;
  }
});

/**
 * 初始化资源文件
 */
async function init() {
  spinning.value = true;
  let { current, pageSize } = ipagination.value;
  let data = {
    current,
    page_size: pageSize,
  };
  let keys = Object.keys(queryParam.value);
  Object.values(queryParam.value).map((_, i) => {
    if (_ !== "") {
      data[keys[i]] = _;
    }
  });
  initMaterialFolder();
  await apiMaterialList(data).then((res) => {
    spinning.value = false;
    if (res.data) {
      let { list, current, page_size, total } = res.data;
      dataSource.value = list.map((_: any) => {
        if (["jpg", "png", "jpeg", "gif"].includes(_.extension)) {
          const img = new Image();
          img.onload = () => {
            _["width"] = img.width;
            _["height"] = img.height;
          };
          img.src = _.url;
        }
        return _;
      });
      Object.assign(ipagination.value, {
        current,
        pageSize: page_size,
        total,
      });
    }
  });
}

function selectDirData(e, { node }) {
  let [a] = e;
  currentPath.value = node.path.split("/");
  if (e.length !== 0) {
    queryParam.value.parent_id = a;
    Object.assign(proxy.$refs.fileUpload.data, {
      parent_id: a,
    });
  } else {
    queryParam.value.parent_id = "";
    Object.assign(proxy.$refs.fileUpload.data, {
      parent_id: "",
    });
  }
  init();
}

const onSearch = () => init();

/**
 * 初始化文件目录数据
 */
async function initMaterialFolder() {
  const request = await apiMaterialFolder({});
  if (request.data) {
    folderTreeData.value = mapDataToTree(request.data);
    let id = "";
    if (folderTreeData.value.length !== 0) {
      id = folderTreeData.value[0].id;
    }
    return Promise.resolve(id);
  }
}

const mapDataToTree = (data) => {
  return data.map((item) => ({
    ...item,
    key: item.id,
    title: item.name,
    children: item.children ? mapDataToTree(item.children) : null,
  }));
};

/**
 * 打开文件夹
 */
function openFolder(e) {
  if (e.type == "dir") {
    queryParam.value.parent_id = e.id;
    actionIndex.value = -1;
    selectedRowKeys.value = [];
    init();
  }
}

const onContextMenuClick = (treeKey: string, menuKey: string | number) => {
  apiMaterialDelete({ id: treeKey }).then((res) => {
    message.success("删除成功");
    initMaterialFolder();
  });
};

/**
 * 删除素材文件
 * @param {Number} id 素材ID
 */
function onDelete() {
  Modal.confirm({
    title: "删除提示",
    icon: createVNode(ExclamationCircleOutlined),
    content: "确认删除选中的文件夹? 请谨慎删除。",
    okText: "确认",
    cancelText: "取消",
    okType: "danger",
    onOk() {
      let array = [];
      selectedRowKeys.value.map((_) => {
        array.push(apiMaterialDelete({ id: _ }));
      });
      Promise.all(array).then((res) => {
        message.success("删除成功");
        init();
        initMaterialFolder();
      });
    },
  });
}

const onSelectAll = () => {
  if (mode.value == "multiple") {
    if (selectedRowKeys.value.length == dataSource.value.length) {
      selectedRowKeys.value = [];
    } else {
      selectedRowKeys.value = dataSource.value.map((k) => k.id);
    }
  }
};

/**
 * 上传文件回调
 */
const uploadSuccessDone = () => init();

function onChangePagination(e) {
  ipagination.value.current = e;
  init();
}

const onToggleLayouts = () => {
  currentLayout.value == "list"
    ? (currentLayout.value = "grid")
    : (currentLayout.value = "list");
};

/**
 * 新建目录
 */
const onCreateDirectory = () => {
  let data = {};
  let { parent_id } = queryParam.value;
  if (parent_id) {
    data["parent_id"] = parent_id;
  }
  apiMaterialCreatedFolder(data).then((res) => {
    message.success(res.message);
    init();
    initMaterialFolder();
  });
};

const onOperateFileOrDir = (params) => {
  switch (params.type) {
    case "dir":
      openFolder(params);
      break;
    default:
      break;
  }
};

const formatBackgroundImage = (params: any) => {
  let { type, thumb_path } = params;
  switch (type) {
    default:
      return getFileIconByExt(type);
  }
};

const onSelectFile = (params: any, idx: any) => {
  if (actionIndex.value == idx) {
    actionIndex.value = -1;
    currentCopyData.value = {};
    isCopy.value = false;
    return false;
  }
  actionIndex.value = idx;
};

const onMultipleChoices = ({ id }, idx: number) => {
  if (selectedRowKeys.value.includes(id)) {
    selectedRowKeys.value.splice(selectedRowKeys.value.indexOf(id), 1);
  } else {
    selectedRowKeys.value.push(id);
  }
};

/**
 * 刷新文件列表
 */
const onRefresh = () => init();

watch(
  () => visible.value,
  (e) => {
    selectedRowKeys.value = [];
    actionIndex.value = -1;
    if (e) {
      nextTick(() => {
        const fileContainer = document.getElementById("file-container");
        tableContentHeight.value = fileContainer.clientHeight;
      });
    }
    if (!e) {
      folderTreeData.value = [];
      dataSource.value = [];
      queryParam.value = {
        keyword: "",
        type: "",
        parent_id: "",
        sort_order: "DESC",
      };
    }
  }
);

watch(
  () => queryParam.value.type,
  (e) => {
    fileUpload.value.typeValue = e ? e : "";
  }
);

watch(
  () => queryParam.value.parent_id,
  (parent_id) => {
    if (parent_id) {
      Object.assign(proxy.$refs.fileUpload.data, {
        parent_id,
      });
    }
  },
  { deep: true }
);

watch(
  () => queryParam.value.parent_id,
  (parent_id) => {
    if (parent_id) {
      Object.assign(proxy.$refs.fileUpload.data, {
        parent_id,
      });
    }
  }
);

const onSort = () => {
  let { sort_order } = queryParam.value;
  sort_order == "DESC"
    ? (queryParam.value.sort_order = "ASC")
    : (queryParam.value.sort_order = "DESC");
  init();
};

const onModifyRename = () => {
  dataSource.value.map((k: any, i: number) => {
    if (i == actionIndex.value) {
      proxy.$refs.rename.visible = true;
      nextTick(() => {
        let { id, name } = k;
        proxy.$refs.rename.init({
          id,
          name,
        });
      });
    }
  });
};

const onCopy = () => {
  let data = dataSource.value[actionIndex.value];
  currentCopyData.value = data;
  isCopy.value = true;
};

const onPaste = () => {
  spinning.value = true;
  let { id } = currentCopyData.value;
  apiMaterialCopy({
    id,
    folder: queryParam.value.parent_id,
  })
    .then((res) => {
      spinning.value = false;
      isCopy.value = false;
      actionIndex.value = -1;
      currentCopyData.value = {};
      init();
    })
    .catch(() => {
      spinning.value = false;
      isCopy.value = false;
      currentCopyData.value = {};
    });
};

const onScissors = () => {
  spinning.value = true;
  let { id } = currentCopyData.value;
  apiMaterialScissors({
    id,
    folder: queryParam.value.parent_id,
  })
    .then((res) => {
      spinning.value = false;
      isCopy.value = false;
      actionIndex.value = -1;
      currentCopyData.value = {};
      init();
    })
    .catch(() => {
      spinning.value = false;
      isCopy.value = false;
      currentCopyData.value = {};
    });
};

const handleOk = () => {
  switch (mode.value) {
    case "multiple":
      let fileList: any = [];
      dataSource.value.map((k: any) => {
        if (selectedRowKeys.value.includes(k.id)) {
          fileList.push(k);
        }
      });
      emit("oks", fileList);
      break;
    case "single":
      if (mode.value == "single") {
        let data = dataSource.value[actionIndex.value];
        emit("oks", data);
      }
      break;
  }
  visible.value = false;
};

defineExpose({
  selectedKeys,
  queryParam,
  visible,
  init,
  initMaterialFolder,
});
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
                  background-image: url("@/assets/images/file-explorer/icon/左2.svg");

                  &.disabled {
                    background-image: url("@/assets/images/file-explorer/icon/左2浅灰.svg");
                  }
                }

                &.ico-right {
                  background-image: url("@/assets/images/file-explorer/icon/右2.svg");

                  &.disabled {
                    background-image: url("@/assets/images/file-explorer/icon/右2浅灰.svg");
                  }
                }

                &.ico-edit {
                  background-image: url("@/assets/images/file-explorer/icon/edit_gray_linear.svg");

                  &.disabled {
                    background-image: url("@/assets/images/file-explorer/icon/edit_light_gray_linear.svg");
                  }
                }

                &.ico-scissors {
                  background-image: url("@/assets/images/file-explorer/icon/剪刀.svg");

                  &.disabled {
                    background-image: url("@/assets/images/file-explorer/icon/剪刀浅灰.svg");
                  }
                }

                &.ico-copy {
                  background-image: url("@/assets/images/file-explorer/icon/复制.svg");

                  &.disabled {
                    background-image: url("@/assets/images/file-explorer/icon/复制浅灰.svg");
                  }
                }

                &.ico-paste {
                  background-image: url("@/assets/images/file-explorer/icon/粘帖.svg");

                  &.disabled {
                    background-image: url("@/assets/images/file-explorer/icon/粘帖浅灰.svg");
                  }
                }

                &.ico-rename {
                  background-image: url("@/assets/images/file-explorer/icon/重命名.svg");

                  &.disabled {
                    background-image: url("@/assets/images/file-explorer/icon/重命名浅灰.svg");
                  }
                }

                &.ico-trash {
                  background-image: url("@/assets/images/file-explorer/icon/垃圾桶.svg");

                  &.disabled {
                    background-image: url("@/assets/images/file-explorer/icon/垃圾桶浅灰.svg");
                  }
                }

                &.ico-lock-on {
                  background-image: url("@/assets/images/file-explorer/icon/lock_on_deep_gray_linear.svg");

                  &.disabled {
                    background-image: url("@/assets/images/file-explorer/icon/lock_on_gray_linear2.svg");
                  }
                }

                &.ico-add-dir {
                  background-image: url("@/assets/images/file-explorer/icon/创建文件夹.svg");
                }

                &.ico-select-all {
                  background-image: url("@/assets/images/file-explorer/icon/全选.svg");
                }

                &.ico-list-layout {
                  background-image: url("@/assets/images/file-explorer/icon/列表.svg");
                }

                &.ico-grid-layout {
                  background-image: url("@/assets/images/file-explorer/icon/网格.svg");
                }

                &.ico-refresh {
                  background-image: url("@/assets/images/file-explorer/icon/refresh_gray_linear.svg");
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
                background-image: url("@/assets/images/file-explorer/icon/上2.svg");
              }

              &.ico-down {
                background-image: url("@/assets/images/file-explorer/icon/下2.svg");
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
            background-image: url("@/assets/images/file-explorer/icon/lock_on_face.svg");
          }

          &:hover {
            .checkbox-wrap {
              .ico-checkbox {
                background-image: url("@/assets/images/file-explorer/icon/checkbox_gray_linear.svg");
              }
            }
          }

          &.selected {
            .checkbox-wrap {
              .ico-checkbox {
                background-image: url("@/assets/images/file-explorer/icon/checkbox_checked_face.svg");
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
          grid-template-columns: repeat(8, 1fr);
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

              .checkbox-wrap {
                display: block;

                .ico-checkbox {
                  background-image: url("@/assets/images/file-explorer/icon/checkbox_gray_linear.svg");
                }
              }
            }

            &.selected {
              cursor: default;

              .checkbox-wrap {
                display: block;

                .ico-checkbox {
                  background-image: url("@/assets/images/file-explorer/icon/checkbox_checked_face.svg");
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