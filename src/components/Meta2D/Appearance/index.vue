<template>
  <div class="app-props">
    <div class="appearance-layout">
      <a-tabs v-model:activeKey="tags">
        <a-tab-pane :key="1" tab="外观">
          <div class="mb-12">
            <a-collapse v-model:activeKey="alignmentKey" size="small" expand-icon-position="right">
              <a-collapse-panel :key="1" header="对齐(参照框)">
                <div class="flex items-center justify-between">
                  <i title="左对齐" class="iconfont icon-juzuoduiqi" @click="onAlignNodes('left')"></i>
                  <i title="右对齐" class="iconfont icon-juyouduiqi" @click="onAlignNodes('right')"></i>
                  <i title="顶部对齐" class="iconfont icon-jushangduiqi" @click="onAlignNodes('top')"></i>
                  <i title="底部对齐" class="iconfont icon-juxiaduiqi" @click="onAlignNodes('bottom')"></i>
                  <i title="垂直居中" class="iconfont icon-zuoyoujuzhongduiqi" @click="onAlignNodes('center')"></i>
                  <i title="水平居中" class="iconfont icon-shangxiajuzhongduiqi" @click="onAlignNodes('middle')"></i>
                  <!-- <Icon
                  title="等距分布、左右对齐"
                  name="component-divider-horizontal"
                />
                <Icon
                  title="等距分布、上下对齐"
                  name="component-divider-vertical"
                /> -->
                  <!-- <i class="t-icon t-horizontal-between"></i> -->
                  <!-- <i
                title="等距分布、上下对齐"
                class="t-icon t-vertical-between"
              ></i> -->
                </div>
              </a-collapse-panel>
              <a-collapse-panel :key="2" header="对齐(参照第一个选中节点)">
                <div class="flex items-center justify-between">
                  <i title="左对齐" class="iconfont icon-juzuoduiqi" @click="onAlignNodesByFirst('left')"></i>
                  <i title="右对齐" class="iconfont icon-juyouduiqi" @click="onAlignNodesByFirst('right')"></i>
                  <i title="顶部对齐" class="iconfont icon-jushangduiqi" @click="onAlignNodesByFirst('top')"></i>
                  <i title="底部对齐" class="iconfont icon-juxiaduiqi" @click="onAlignNodesByFirst('bottom')"></i>
                  <i title="垂直居中" class="iconfont icon-zuoyoujuzhongduiqi" @click="onAlignNodesByFirst('center')"></i>
                  <i title="水平居中" class="iconfont icon-shangxiajuzhongduiqi" @click="onAlignNodesByFirst('middle')"></i>
                </div>
              </a-collapse-panel>
              <!-- <a-collapse-panel :key="2" header="样式">
                <a-form label-align="left" :label-col="{ span: 10 }">
                  <a-form-item label="边框宽度">
                    <a-input-number
                      v-model:value="model.borderWidth"
                      @change="changeValue('borderWidth')"
                      style="width: 100%"
                    />
                  </a-form-item>
                </a-form>
              </a-collapse-panel> -->
            </a-collapse>
          </div>
        </a-tab-pane>
        <a-tab-pane :key="2" tab="布局"></a-tab-pane>
        <a-tab-pane :key="3" tab="结构"></a-tab-pane>
      </a-tabs>
    </div>
  </div>
</template>

<script>
import { ref, watch, nextTick, defineComponent } from 'vue';
import { Icon } from 'tdesign-icons-vue-next';
import { useCommonStore } from '@/store/modules/common';
export default defineComponent({
  components: { Icon },
  setup(props, { emit }) {
    let pens = ref([]);

    let tags = ref(1);

    let model = ref({});

    let alignmentKey = ref([1, 2, 3]);

    const init = (data) => {
      pens.value = data;
    };

    const onAlignNodes = (key) => {
      meta2d.alignNodes(key, pens.value);
    };

    const onAlignNodesByFirst = (key) => {
      meta2d.alignNodesByFirst(key, pens.value);
    };

    const changeValue = (prop) => {
      let list = pens.value;
      list.map((v) => {
        v[prop] = model.value[prop];
        // meta2d.updateValue(v, { [prop]: model.value[prop] });
      });
      // const v = { id: pen.value.id };
      // v[prop] = pen.value[prop];
      // switch (prop) {
      //   case "dash":
      //     let key = v[prop];
      //     configLineDash.map((_, idx) => {
      //       if (key == idx) {
      //         v["lineDash"] = JSON.parse(_.value);
      //       }
      //     });
      //     break;
      //   default:
      //     break;
      // }
      // meta2d.setValue(v, { render: true });
    };

    return {
      pens,
      tags,
      model,
      alignmentKey,
      init,
      changeValue,
      onAlignNodes,
      onAlignNodesByFirst,
    };
  },
});
</script>

<style lang="less" scoped>
.app-props {
  height: calc(100vh - 40px);
  padding: 0 12px;
  border-left: 1px solid #dddddd;
  overflow-y: auto;
  z-index: 2;
  .appearance-layout {
    :deep .ant-tabs {
      .ant-collapse-content {
        .ant-collapse-content-box {
          padding: 6px;
        }
        i {
          cursor: pointer;
          &::before {
            font-size: 22px;
          }
        }
        .t-icon {
          cursor: pointer;
        }
      }
    }
  }
}
</style>