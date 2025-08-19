<!--
 * @Descripttion:
 * @version: 1.0.0
 * @Author: htang
 * @Date: 2023-10-12 17:49:12
 * @LastEditors: htang
 * @LastEditTime: 2025-08-18 19:55:48
-->
<template>
  <a-modal
    v-model:visible="visible"
    centered
    width="45%"
    :destroyOnClose="true"
    wrapClassName="editor-modal"
    cancelText="取消"
    :footer="true"
    okText="确定"
  >
    <template #title>
      <div class="flex items-center">
        <span>图形库管理</span>
        <a-divider type="vertical" />
        <redo-outlined @click="onRefresh" title="刷新" />
      </div>
    </template>
    <div class="m-4">
      <div class="mb-6">
        <a-checkbox v-model:checked="checkall" @change="onCheckAllChange"
          >全选</a-checkbox
        >
      </div>
      <a-checkbox-group v-model:value="dataValue" style="width: 100%">
        <a-row :gutter="[16, 16]">
          <template v-for="(vo, idx) in checkedList" :key="idx">
            <a-col :span="8">
              <a-checkbox :value="vo.id">{{ vo.label }}</a-checkbox>
            </a-col>
          </template>
        </a-row>
      </a-checkbox-group>
    </div>
  </a-modal>
</template>

<script>
import { ref, defineComponent, getCurrentInstance, watch } from "vue";
import { message } from "ant-design-vue";
import { RedoOutlined } from "@ant-design/icons-vue";
import { useCommonStore } from "@/store/modules/common";
import { GRAPHIC_GROUPS } from "@/utils/graphicGroups";
import { setGraphicGroups } from "@/utils/meta-storage";

export default defineComponent({
  components: { RedoOutlined },
  setup(props, { emit }) {
    let { proxy } = getCurrentInstance();

    let visible = ref(false);

    let dataValue = ref([]);

    let checkedList = ref([]);

    let checkall = ref(true);

    let indeterminate = ref(false);

    watch(
      () => dataValue.value,
      (params) => {
        indeterminate.value =
          !!params.length && params.length < checkedList.value.length;
        checkall.value =
          params.length > 0 && params.length === checkedList.value.length;
        let obj = useCommonStore().graphics;
        checkedList.value.map((_) => {
          if (!dataValue.value.includes(_.id)) {
            _.value = false;
          } else {
            _.value = true;
          }
          obj[_.label] = _.value;
        });
        setGraphicGroups(obj);
        emit("oks");
      }
    );

    /**
     * 初始化多选框设置
     */
    function init() {
      reset();
      let obj = useCommonStore().graphics;
      let keys = Object.keys(obj);
      Object.values(obj).map((_, idx) => {
        checkedList.value.push({
          id: idx,
          label: keys[idx],
          value: _,
        });
      });
      checkedList.value.map((_, i) => {
        if (_.value == true) {
          dataValue.value.push(i);
        }
      });
    }

    function reset() {
      checkall.value = ref(true);
      checkedList.value = [];
      dataValue.value = [];
    }

    function onCheckAllChange(e) {
      dataValue.value = e.target.checked
        ? checkedList.value.map((item) => item.id)
        : [];
      indeterminate.value = false;
    }

    /**
     * 刷新缓存
     */
    function onRefresh() {
      let obj = {};
      GRAPHIC_GROUPS.map((_) => {
        obj[_.name] = _.show;
      });
      setGraphicGroups(obj);
      useCommonStore().setGraphicGroups(obj);
      init();
      message.success("刷新成功");
    }

    return {
      visible,
      dataValue,
      checkedList,
      checkall,
      indeterminate,
      init,
      onCheckAllChange,
      onRefresh,
    };
  },
});
</script>