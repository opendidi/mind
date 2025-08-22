<!--
 * @Descripttion:
 * @version: 1.0.0
 * @Author: htang
 * @Date: 2025-08-22 15:52:34
 * @LastEditors: htang
 * @LastEditTime: 2025-08-22 16:24:56
-->
<template>
  <a-modal
    v-model:visible="visible"
    title="图纸列表"
    width="60%"
    centered
    :destroyOnClose="true"
    :bodyStyle="{
      padding: '12px',
    }"
    wrapClassName="blueprint-modal"
    @ok="handleOk"
    @onCancel="handleCancel"
  >
    <div class="blueprint-list">
      <template v-if="dataSource.length !== 0">
        <ul class="grid grid-cols-6 gap-2">
          <template v-for="(item, index) in dataSource" :key="index">
            <li class="cursor-pointer" :title="item.name">
              <div class="thumb">
                <img :src="item.thumbnail" alt="" />
              </div>
              <div class="name">
                <span>{{ item.name }}</span>
              </div>
            </li>
          </template>
        </ul>
      </template>
      <template v-else>
        <a-empty description="暂没图纸数据" />
      </template>
    </div>
  </a-modal>
</template>

<script setup>
import { ref, watch } from "vue";
import { apiBlueprintList } from "@/api/blueprint";

const visible = ref(false);

const queryParam = ref({});

const dataSource = ref([]);

const ipagination = ref({
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

watch(
  () => visible.value,
  (val) => {
    if (val) {
      init();
    }
  }
);

const init = () => {
  const { current, pageSize } = ipagination.value;
  let data = {
    current,
    page_size: pageSize,
  };
  apiBlueprintList(data).then((res) => {
    let { list, current, total, page_size } = res;
    dataSource.value = list;
    Object.assign(ipagination.value, {
      current,
      total,
      pageSize: page_size,
    });
    console.log(res);
  });
};

const handleOk = () => {};

const handleCancel = () => {
  visible.value = false;
};

defineExpose({
  visible,
});
</script>

<style lang="less" scoped>
.blueprint-modal {
  .blueprint-list {
    ul {
      padding: 0;
      margin: 0;
      li {
        width: 100%;
        border: 1px solid #f0f0f0;
        box-sizing: border-box;
        border-radius: 8px;
        .thumb {
          height: 180px;
          border-radius: 8px 8px 0 0;
          img {
            width: 100%;
          }
        }
        .name {
          margin-top: 10px;
          font-size: 18px;
          font-weight: bold;
          text-align: center;
        }
      }
    }
  }
}
</style>