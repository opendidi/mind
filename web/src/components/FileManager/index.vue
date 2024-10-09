<!--
 * @Descripttion:
 * @version: 1.0.0
 * @Author: htang
 * @Date: 2024-09-24 16:38:51
 * @LastEditors: htang
 * @LastEditTime: 2024-09-29 09:44:03
-->
<template>
  <a-modal
    v-model:visible="visible"
    title="资源文件管理器"
    :footer="false"
    width="65%"
    :bodyStyle="bodyStyle"
    :destroyOnClose="true"
    centered
  >
    <a-spin tip="素材加载中..." :spinning="spinning">
      <div class="file-manager">
        <div class="file-head">
          <a-form layout="inline">
            <a-form-item label="文件名称">
              <a-input-search
                v-model:value="queryParam.keyword"
                placeholder="请输入文件名称搜索"
                enter-button="搜索"
                @search="onSearch"
                allowClear
              >
                <template #suffix>
                  <SearchOutlined />
                </template>
              </a-input-search>
            </a-form-item>
            <a-form-item>
              <CreatedFolder ref="createdFolder" @oks="successCreatedFolder" />
            </a-form-item>
            <a-form-item>
              <FileUpload ref="fileUpload" @oks="uploadSuccessDone" />
            </a-form-item>
          </a-form>
        </div>
        <div class="folder-tree">
          <template v-if="folderTreeData.length !== 0">
            <a-tree
              v-model:selectedKeys="selectedKeys"
              :tree-data="folderTreeData"
              default-expand-all
              show-icon
              block-node
              @select="selectFolderData"
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
        <div class="file-container">
          <template v-if="dataSource.length !== 0">
            <a-table
              rowKey="id"
              :dataSource="dataSource"
              :columns="columns"
              :row-selection="{ selectedRowKeys, onChange: onSelectChange }"
              :custom-row="customRow"
              :pagination="false"
              size="small"
            >
              <template v-slot:bodyCell="{ column, record, index }">
                <template v-if="column.dataIndex == 'name'">
                  <div @dblclick.stop.native="openFolder(record)">
                    <template v-if="record.type == 'panorama'">
                      <img
                        src="@/assets/images/files/jpg.svg"
                        alt=""
                        width="20px"
                      />
                    </template>
                    <template v-if="record.type == 'folder'">
                      <img
                        src="@/assets/images/files/folder.svg"
                        alt=""
                        width="20px"
                      />
                    </template>
                    <span style="margin: 0 0 0 6px">{{ record.name }}</span>
                  </div>
                </template>
                <template v-if="column.dataIndex == 'action'">
                  <template v-if="['image', 'panorama'].includes(record.type)">
                    <span class="image-gallery">
                      <a @click.stop.native="openPreview(record)">查看</a>
                      <a-divider type="vertical" />
                    </span>
                  </template>
                  <a @click.stop.native="handleDeleteFile(record)">删除</a>
                </template>
              </template>
            </a-table>
            <div class="table-footer">
              <a-button
                :disabled="selectedRowKeys.length == 0 ? true : false"
                @click="getFile"
              >
                已选择文件({{ selectedRowKeys.length }})
              </a-button>
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
  </a-modal>
</template>

<script lang="ts" setup>
import {
  ref,
  createVNode,
  onMounted,
  getCurrentInstance,
  watch,
  nextTick,
} from "vue";
import {
  apiMaterialList,
  apiMaterialFolder,
  apiMaterialDelete,
} from "@/api/material";
import CreatedFolder from "./components/createdFolder.vue";
import FileUpload from "./components/upload.vue";
import FilePreview from "./components/preview.vue";
import { Modal, Empty, message } from "ant-design-vue";
import {
  FolderOutlined,
  FolderOpenOutlined,
  ExclamationCircleOutlined,
  SearchOutlined,
  DeleteOutlined,
} from "@ant-design/icons-vue";

const simpleImage = Empty.PRESENTED_IMAGE_SIMPLE;

const emit = defineEmits(["oks"]);

const bodyStyle = ref({
  padding: "0 12px 12px",
});

let { proxy } = getCurrentInstance();

let queryParam = ref({
  keyword: "",
  type: "",
  parent_id: "",
});

let selectedKeys = ref([]);

let spinning = ref(false);

let visible = ref(false);

let popoverVisible = ref(false);

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

let columns = ref([
  {
    title: "文件名称",
    dataIndex: "name",
  },
  {
    title: "文件大小",
    dataIndex: "size",
  },
  {
    title: "文件格式",
    dataIndex: "extension",
  },
  {
    title: "创建时间",
    dataIndex: "created_at",
  },
  {
    title: "操作",
    dataIndex: "action",
  },
]);

let activeKey = ref("panorama");

/**
 * 初始化资源文件
 */
function initMaterialList() {
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
  apiMaterialList(data).then((res) => {
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

async function init() {
  await initMaterialFolder().then((id) => {
    selectedKeys.value = [id];
    queryParam.value.parent_id = id;
    Object.assign(proxy.$refs.createdFolder.model, {
      parent_id: id,
    });
    Object.assign(proxy.$refs.fileUpload.data, {
      parent_id: id,
    });
  });
  await initMaterialList();
}

/**
 * 预览图片
 */
function openPreview(record) {
  proxy.$refs.filePreview.openPreview(record);
}

function selectFolderData([a]) {
  queryParam.value.parent_id = a;
  Object.assign(proxy.$refs.createdFolder.model, {
    parent_id: a,
  });
  Object.assign(proxy.$refs.fileUpload.data, {
    parent_id: a,
  });
  initMaterialList();
}

function onSearch() {
  initMaterialList();
}

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
 * 新建完文件夹后刷新数据
 */
function successCreatedFolder() {
  initMaterialFolder();
  initMaterialList();
}

const selectRow = (record) => {
  let keys = [].concat(selectedRowKeys.value);
  if (keys.includes(record.id)) {
    keys.splice(keys.indexOf(record.id), 1);
  } else {
    keys.push(record.id);
  }
  selectedRowKeys.value = keys;
};

/**
 * 打开文件夹
 */
function openFolder(e) {
  if (e.type == "folder") {
    console.log(e);
  }
}

const customRow = (record) => {
  return {
    onClick: (event) => {
      event.stopPropagation();
      selectRow(record);
    },
  };
};

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
function handleDeleteFile(data) {
  let { id } = data;
  Modal.confirm({
    title: "删除提示",
    icon: createVNode(ExclamationCircleOutlined),
    content: "确定删除这文件?",
    okText: "确认",
    cancelText: "取消",
    okType: "danger",
    onOk() {
      apiMaterialDelete({ id }).then((res) => {
        initMaterialFolder();
      });
    },
  });
}

function onSelectChange(keys: any) {
  selectedRowKeys.value = keys;
}

/**
 * 获取需要的文件
 */
function getFile() {
  const keys = selectedRowKeys.value;
  let fileList = [];
  dataSource.value.map((k) => {
    if (keys.includes(k.id)) {
      fileList.push(k);
    }
  });
  visible.value = false;
  selectedRowKeys.value = [];
  emit("oks", fileList);
}

/**
 * 上传文件回调
 */
function uploadSuccessDone() {
  initMaterialList();
}

function onChangePagination(e) {
  ipagination.value.current = e;
  initMaterialList();
}

watch(
  () => activeKey.value,
  (e) => {
    switch (e) {
      case "panorama":
        break;
    }
  }
);

watch(
  () => visible.value,
  (e) => {
    if (!e) {
      folderTreeData.value = [];
      dataSource.value = [];
    }
  }
);

defineExpose({
  init,
  initMaterialFolder,
  visible,
});
</script>

<style lang="less" scoped>
.file-manager {
  display: flex;
  padding: 0 12px;
  justify-content: space-between;
  flex-wrap: wrap;
  .file-head {
    display: flex;
    width: 100%;
    height: 45px;
    margin: 0 0 12px;
    align-items: center;
  }
  .folder-tree {
    width: 200px;
    margin: 0 12px 0 0;
  }
  .file-container {
    border-left: 1px solid #d9d9d9;
    box-sizing: border-box;
    flex: 1;
    :deep(.ant-table) {
      margin: 0 0 12px;
    }
    .table-footer {
      display: flex;
      margin: 0 12px;
      align-items: center;
      justify-content: space-between;
      .ant-pagination {
        text-align: right;
      }
    }
  }
}
</style>