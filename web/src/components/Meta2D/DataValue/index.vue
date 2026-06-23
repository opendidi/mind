<!--
 * @Descripttion:
 * @version: 1.0.0
 * @Author: htang
 * @Date: 2023-09-20 20:00:38
 * @LastEditors: htang
 * @LastEditTime: 2024-01-26 14:19:52
-->
<template>
  <a-form label-align="left" :label-col="{ span: 4 }">
    <a-form-item label="ID">
      <a-input v-model:value="pen.id" @blur="onUpdatePen" />
    </a-form-item>
    <a-form-item label="名称">
      <a-input v-model:value="pen.name" @blur="onUpdatePen" />
    </a-form-item>
  </a-form>
  <a-collapse v-model:activeKey="activeKey" size="small" expand-icon-position="right">
    <a-collapse-panel :key="1" :forceRender="true" header="Tag标签">
      <a-form label-align="left" class="data-value-form">
        <template v-if="pen['tags'].length !== 0">
          <a-form-item>
            <div class="flex flex-wrap">
              <template v-for="(vo, idx) in pen.tags" :key="idx">
                <a-tag>
                  <template #icon>
                    {{ vo }}
                    <close-outlined @click="onClosePenTag(idx)" />
                  </template>
                </a-tag>
              </template>
            </div>
          </a-form-item>
        </template>
        <a-form-item>
          <a-input v-model:value="tags.text" @keyup.enter="addPenTags" placeholder="按回车添加(最大长度100)" />
        </a-form-item>
      </a-form>
    </a-collapse-panel>
    <a-collapse-panel :key="2" :forceRender="true" header="数据">
      <a-form label-align="left" :label-col="{ span: 10 }" class="data-value-form">
        <template v-if="pen.form !== undefined && pen.form.length !== 0">
          <template v-for="(vo, idx) in pen.form" :key="idx">
            <a-form-item :label="vo.name">
              <div class="flex items-center justify-between">
                <template v-if="vo.type == 'text'">
                  <a-input
                    v-model:value="pen[vo.key]"
                    @change="getDataValue(vo.key, pen[vo.key])"
                    style="width: 100%"
                  />
                </template>
                <template v-else-if="vo.type == 'number'">
                  <a-input-number
                    v-model:value="pen[vo.key]"
                    style="flex: 1"
                    @change="getDataValue(vo.key, pen[vo.key])"
                  />
                </template>
                <template v-else-if="vo.type == 'switch'">
                  <a-switch v-model:checked="pen[vo.key]" />
                </template>
                <template v-else-if="vo.type == 'code'">
                  <a-button size="small" @click="openEditContainer(vo, idx)">...</a-button>
                </template>
                <template v-else-if="vo.type == 'slider'">
                  <a-slider
                    v-model:value="pen[vo.key]"
                    :min="vo.min"
                    :max="vo.max"
                    :step="vo.step"
                    @change="getDataValue(vo.key, pen[vo.key])"
                    style="flex: 1"
                  />
                </template>
                <div class="flex variable" style="flex: 1">
                  <LinkOutlined title="绑定变量" @click="openVariable(vo, idx)" />
                  <DeleteOutlined title="删除" @click="onDeleteData(vo, idx)" />
                </div>
              </div>
              <template v-if="vo.dataIds.dataId !== ''">
                <div class="flex items-center justify-between data-id">
                  <span>{{ vo.dataIds.dataId }}</span>
                  <DeleteOutlined title="删除" @click="onDeleteDataIds(vo, idx)" />
                </div>
              </template>
            </a-form-item>
          </template>
          <a-form-item>
            <a-button @click="onAdd" style="width: 100%">
              <template #icon>
                <plus-outlined />
              </template>
              <span>新增</span>
            </a-button>
          </a-form-item>
        </template>
        <template v-else>
          <a-empty :image="simpleImage">
            <template #description>
              <span>
                暂无数据，
                <a @click="onAdd">添加</a>
              </span>
            </template>
          </a-empty>
        </template>
      </a-form>
    </a-collapse-panel>
    <template v-if="pen['dropdownList']">
      <a-collapse-panel :key="3" :forceRender="true" header="下拉列表">
        <div class="dropdown-list">
          <ul>
            <template v-for="(vo, idx) in pen['dropdownList']" :key="idx">
              <li class="flex items-center justify-between">
                <span :title="vo.text">{{ vo.text }}</span>
                <span>
                  <a-button type="link" size="small" title="编辑" @click="onEditSelect(idx)">
                    <template #icon>
                      <edit-outlined />
                    </template>
                  </a-button>
                  <a-button type="link" size="small" @click="onDeleteSelectData(vo, idx)" title="删除" danger>
                    <template #icon>
                      <delete-outlined />
                    </template>
                  </a-button>
                </span>
              </li>
            </template>
          </ul>
          <a-button @click="onAddSelect" style="width: 100%">
            <template #icon>
              <plus-outlined />
            </template>
            <span>新增</span>
          </a-button>
        </div>
      </a-collapse-panel>
    </template>
  </a-collapse>
  <DataDrawer ref="dataDrawerRef" @oks="getDataDrawer" />
  <VariableModal ref="variableModalRef" @oks="getDataId" />
  <SelectForm ref="selectFormRef" @oks="getSelectFormData" />
  <EditContainer ref="editContainerRef" @oks="getEditTextValue" />
</template>

<script>
import { ref, watch, defineComponent, nextTick } from 'vue'
import { CloseOutlined, EditOutlined, DeleteOutlined, LinkOutlined, PlusOutlined } from '@ant-design/icons-vue'
import { useSelection } from '@/services/selections'
import { Empty, message } from 'ant-design-vue'
import DataDrawer from './components/form.vue'
import VariableModal from './components/variable.vue'
import SelectForm from './components/selectForm.vue'
import EditContainer from '@/components/Meta2D/EditContainer/index.vue'
let dataIndex = -1
export default defineComponent({
  components: {
    PlusOutlined,
    LinkOutlined,
    EditOutlined,
    DeleteOutlined,
    DataDrawer,
    VariableModal,
    CloseOutlined,
    SelectForm,
    EditContainer,
  },
  emits: ['oks', 'getDataValue', 'deleteDataValue'],
  setup(props, { emit }) {
    const { selections } = useSelection()

    const dataDrawerRef = ref(null)
    const variableModalRef = ref(null)
    const selectFormRef = ref(null)
    const editContainerRef = ref(null)

    const activeKey = ref([1, 2])

    const pen = ref({
      tags: [],
    })

    const tags = ref({
      text: '',
    })

    function init(_) {
      pen.value = {
        tags: [],
      }
      Object.assign(pen.value, {
        ..._,
      })
    }

    function onAdd() {
      dataDrawerRef.value.visible = true
    }

    function getDataDrawer(model) {
      if (!pen.value['form']) {
        pen.value['form'] = []
      }
      switch (model.type) {
        case 'text':
          pen.value[model.key] = ''
          break
        case 'switch':
          pen.value[model.key] = true
          break
        case 'number':
          pen.value[model.key] = model.min
          break
      }
      pen.value.form.push({
        ...model,
        dataIds: {
          dataId: '',
          name: '',
        },
      })
      emit('oks', pen.value)
    }

    /**
     * 打开代码编辑器
     */
    function openEditContainer(data, index) {
      editContainerRef.value.visible = true
      dataIndex = index
      nextTick(() => {
        let value = pen.value[data.key]
        editContainerRef.value.init(value ? value : '')
      })
    }

    /**
     * 获取代码编辑器返回值
     */
    function getEditTextValue(textValue) {
      if (dataIndex >= 0 && pen.value.form) {
        const formItem = pen.value.form[dataIndex]
        pen.value[formItem.key] = textValue
        emit('oks', pen.value)
      }
      dataIndex = -1
    }

    /**
     * 删除数据选项
     * @param {Object} data
     * @param {Number} idx
     */
    function onDeleteData(data, idx) {
      pen.value.form.splice(idx, 1)
      emit('deleteDataValue', data.key)
    }

    function getDataValue(k, v) {
      emit('getDataValue', k, v)
    }

    /**
     * 打开变量弹窗
     */
    const openVariable = (data, index) => {
      variableModalRef.value.visible = true
      dataIndex = index
    }

    /**
     * 获取绑定变量ID
     */
    function getDataId(e) {
      let { id, name } = e
      Object.assign(pen.value.form[dataIndex], {
        dataIds: {
          dataId: id,
          name,
        },
      })
      dataIndex = -1
    }

    function onDeleteDataIds(vo, idx) {
      pen.value.form[idx].dataIds = {
        dataId: '',
        name: '',
      }
    }

    function addPenTags() {
      if (tags.value['text'] == '') {
        message.warning('文本不能为空')
        return false
      }
      pen.value['tags'].push(tags.value['text'])
      tags.value['text'] = ''
      emit('oks', pen.value)
    }

    function onClosePenTag(idx) {
      pen.value['tags'].splice(idx, 1)
      emit('oks', pen.value)
    }

    /**
     *
     */
    function onAddSelect() {
      selectFormRef.value.visible = true
    }

    function onEditSelect(idx) {
      selectFormRef.value.visible = true
      nextTick(() => {
        selectFormRef.value.init(pen.value['dropdownList'][idx], idx)
      })
    }

    /**
     * 删除下拉选项
     */
    function onDeleteSelectData(data, index) {
      pen.value['dropdownList'].splice(index, 1)
    }

    /**
     * 获取下拉框数据
     */
    function getSelectFormData(data, idx) {
      if (idx !== '') {
        pen.value['dropdownList'][idx] = data
      } else {
        pen.value['dropdownList'].push(data)
      }
    }

    function onUpdatePen() {
      emit('oks', pen.value)
    }

    watch(
      () => selections.pen,
      val => {
        init(val)
      },
    )

    return {
      pen,
      activeKey,
      init,
      tags,
      onDeleteData,
      onAdd,
      getDataDrawer,
      openEditContainer,
      getEditTextValue,
      getDataValue,
      openVariable,
      getDataId,
      onDeleteDataIds,
      addPenTags,
      onClosePenTag,
      onAddSelect,
      onEditSelect,
      onUpdatePen,
      onDeleteSelectData,
      getSelectFormData,
      simpleImage: Empty.PRESENTED_IMAGE_SIMPLE,
      dataDrawerRef,
      variableModalRef,
      selectFormRef,
      editContainerRef,
    }
  },
})
</script>

<style lang="less" scoped>
.ant-collapse {
  .data-value-form {
    .ant-form-item {
      margin-bottom: 12px;
      .ant-tag {
        padding: 0 0px 0 6px;
        margin: 0 6px 6px 0;
      }
      &:last-child {
        margin-bottom: 0;
      }
      .data-id {
        margin: 6px 0 0;
      }
      &:last-child {
        margin-bottom: 0;
      }
      .ant-slider {
        flex: 1;
      }
      .variable {
        .anticon-link,
        .anticon-delete {
          width: 25px;
        }
      }
    }
  }
  .dropdown-list {
    ul {
      padding: 0;
      margin: 0 0 12px;
      li {
        height: 30px;
        border-bottom: 1px solid #f0f0f0;
        box-sizing: border-box;
        line-height: 30px;
        &:last-child {
          border: none;
        }
      }
    }
  }
}
</style>
