<!--
 * @Descripttion:
 * @version: 1.0.0
 * @Author: htang
 * @Date: 2023-09-21 09:31:05
 * @LastEditors: htang
 * @LastEditTime: 2024-01-08 15:09:23
-->
<template>
  <a-modal
    v-model:visible="visible"
    title="绑定变量"
    width="45%"
    wrapClassName="variable-modal"
    okText="确定"
    cancelText="取消"
    @ok="handleOk"
    @cancel="handleCancel"
  >
    <div class="m-4">
      <!-- <div class="flex items-center">
        <span>当前绑定：</span>
        <span>{{ model.dataId }}</span>
        <template v-if="model.dataId !== ''">
          <a-button type="link" size="small" danger>
            <template #icon>
              <delete-outlined />
            </template>
          </a-button>
        </template>
        <template v-else>
          <span>无</span>
        </template>
      </div> -->
      <a-form ref="form" :model="model">
        <!-- <a-form-item name="dataId">
          <a-input v-model:value="model.dataId" placeholder="Search">
            <template #suffix>
              <search-outlined />
            </template>
          </a-input>
        </a-form-item> -->
        <a-form-item>
          <a-radio-group v-model:value="model.dataId" name="radioGroup">
            <a-row :gutter="5">
              <template v-for="(item, idx) in treeData" :key="idx">
                <a-col class="gutter-row" :span="6">
                  <a-radio :value="item.id">{{ item.name }}</a-radio>
                </a-col>
              </template>
            </a-row>
          </a-radio-group>
          <!-- <a-tree :tree-data="treeData" :fieldNames="fieldNames" @select="onSelect" /> -->
        </a-form-item>
      </a-form>
    </div>
  </a-modal>
</template>

<script>
import { ref, defineComponent, onMounted } from 'vue';
import { useCommonStoreWithOut } from '@/store/modules/common';
import { DeleteOutlined, SearchOutlined } from '@ant-design/icons-vue';
import { TREE_LIST as treeList } from './tree';
export default defineComponent({
  components: { SearchOutlined, DeleteOutlined },
  setup(props, { emit }) {
    let visible = ref(false);

    let model = ref({
      name: '',
      dataId: '',
    });

    let treeData = ref([]);

    let fieldNames = ref({
      key: 'id',
      title: 'name',
      children: 'children',
    });

    function handleOk() {
      visible.value = false;
      let data = treeData.value.find((item) => item.id == model.value.dataId);
      if (data) {
        emit('oks', {
          ...data,
        });
      }
    }

    const handleCancel = () => {
      model.value = {
        name: '',
        dataId: '',
      };
    };

    const onSelect = ([dataId]) => {
      if (dataId.indexOf('device') == -1) {
        model.value.dataId = dataId;
      }
    };

    onMounted(() => {
      treeData.value = useCommonStoreWithOut().variableData;
    });

    return {
      visible,
      model,
      treeData,
      fieldNames,
      onSelect,
      handleOk,
      handleCancel,
    };
  },
});
</script>

<style lang="less" scoped>
.variable-modal {
  .ant-modal-body {
    .anticon {
      cursor: pointer;
    }
    .ant-form {
      margin: 12px 0 0;
    }
  }
}
</style>