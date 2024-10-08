<!--
 * @Descripttion:
 * @version: 1.0.0
 * @Author: htang
 * @Date: 2023-09-14 17:27:29
 * @LastEditors: htang
 * @LastEditTime: 2024-02-02 09:25:37
-->
<template>
  <a-modal
    v-model:visible="visible"
    :title="title"
    @ok="handleOk"
    width="80%"
    centered
    :destroyOnClose="true"
    wrapClassName="editor-modal"
    :cancel-button-props="{ style: { display: 'none' } }"
  >
    <div ref="editContainer" :id="'edit-' + uuid" class="code-editor"></div>
    <span>打开图纸后，执行的初始脚本。 <br />可获取pen和context参数 <br />例如，console.log('pen', 'context');return true;</span>
  </a-modal>
</template>

<script>
import { ref, defineComponent, getCurrentInstance, onMounted, watch, onUnmounted } from 'vue';
import { buildUUID } from '@/utils/uuid';
import * as monaco from 'monaco-editor/esm/vs/editor/editor.main.js';
// https://juejin.cn/post/7150587036729737252 参考
import tsWorker from 'monaco-editor/esm/vs/language/typescript/ts.worker?worker';
import jsonWorker from 'monaco-editor/esm/vs/language/json/json.worker?worker';
// 解决vite Monaco提示错误
self.MonacoEnvironment = {
  getWorker(_, label) {
    if (label === 'json') {
      return new jsonWorker();
    }
    if (['typescript', 'javascript'].includes(label)) {
      return new tsWorker();
    }
  },
};
export default defineComponent({
  props: {
    title: {
      type: String,
      default: 'JavaScript',
    },
  },
  emits: ['oks', 'close'],
  setup(props, { emit }) {
    let { proxy } = getCurrentInstance();

    let visible = ref(false);
    let monacoEditor = null;

    let uuid = ref();

    let type = '';

    function init(value, language = 'JavaScript', t) {
      monacoEditor = monaco.editor.create(proxy.$refs.editContainer, {
        value,
        readOnly: false,
        language,
        theme: 'vs-dark',
        selectOnLineNumbers: true,
        renderSideBySide: false,
      });
      type = t;
    }

    watch(
      () => visible.value,
      (bool) => {
        if (!bool) {
          emit('close');
          if (monacoEditor) {
            monacoEditor.dispose();
          }
        } else {
          uuid.value = buildUUID();
        }
      }
    );

    function setMonacoEditorValue(dataValue) {
      monacoEditor.setValue(dataValue);
    }

    function handleOk() {
      emit('oks', monacoEditor.getValue(), type);
      visible.value = false;
      monacoEditor.dispose();
    }

    onUnmounted(() => {
      if (monacoEditor) {
        monacoEditor.dispose();
      }
    });

    return {
      visible,
      uuid,
      handleOk,
      setMonacoEditorValue,
      init,
    };
  },
});
</script>

<style lang="less" >
.ant-modal-root .editor-modal {
  .ant-modal-body {
    padding: 0;
    .code-editor {
      width: 100%;
      height: 80vh;
    }
  }
}
</style>