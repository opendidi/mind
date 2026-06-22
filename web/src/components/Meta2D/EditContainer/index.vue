<!--
 * @Descripttion:
 * @version: 1.0.0
 * @Author: htang
 * @Date: 2023-09-14 17:27:29
 * @LastEditors: htang
 * @LastEditTime: 2026-06-18 14:45:44
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
    <div
      ref="editContainerRef"
      class="code-editor"
      :style="{ height: editorHeight }"
    ></div>
    <span
      >打开图纸后，执行的初始脚本。 <br />可获取pen和context参数
      <br />例如，console.log('pen', 'context');return true;</span
    >
  </a-modal>
</template>

<script>
import {
  ref,
  defineComponent,
  watch,
  onUnmounted,
} from "vue";

// Lazy-loaded monaco module singleton
let monacoModule = null;
async function getMonaco() {
  if (!monacoModule) {
    monacoModule = await import("monaco-editor/esm/vs/editor/editor.main.js");
  }
  return monacoModule;
}

// Persistent editor instance — created once, reused across opens
let monacoEditor = null;
let persistentContainer = null;
let editorReady = false;
let currentType = "";

function computeEditorHeight(value) {
  const lineCount = (value || "").split("\n").length;
  const lineHeight = 21;
  const padding = 48;
  const idealHeight = lineCount * lineHeight + padding;
  const minHeight = Math.max(450, window.innerHeight * 0.4);
  return (
    Math.min(window.innerHeight * 0.8, Math.max(minHeight, idealHeight)) + "px"
  );
}

async function ensureEditor(emit, container) {
  if (editorReady && monacoEditor) return;

  const monaco = await getMonaco();

  // Create persistent hidden container for the editor
  if (!persistentContainer) {
    persistentContainer = document.createElement("div");
    persistentContainer.id = "monaco-persistent-container";
    persistentContainer.style.cssText =
      "position:fixed;top:-9999px;left:0;width:100%;height:80vh;pointer-events:none;";
    document.body.appendChild(persistentContainer);
  }

  monacoEditor = monaco.editor.create(persistentContainer, {
    value: "",
    readOnly: false,
    language: "javascript",
    theme: "vs-dark",
    minimap: { enabled: false },
    scrollBeyondLastLine: false,
    lineNumbersMinChars: 3,
    automaticLayout: true,
    wordWrap: "on",
    tabSize: 2,
    selectOnLineNumbers: true,
    renderSideBySide: false,
  });

  // Ctrl+S triggers save
  monacoEditor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyS, () => {
    emit("oks", monacoEditor.getValue(), currentType);
  });

  editorReady = true;
}

export default defineComponent({
  props: {
    title: {
      type: String,
      default: "JavaScript",
    },
  },
  emits: ["oks", "close"],
  setup(props, { emit }) {
    const editContainerRef = ref(null);

    const visible = ref(false);
    const editorHeight = ref("80vh");
    const language = ref("javascript");

    async function init(value, lang = "JavaScript", t) {
      language.value = (lang || "javascript").toLowerCase();
      currentType = t || "";

      await ensureEditor(emit, editContainerRef.value);

      // Update language if needed
      const monaco = await getMonaco();
      const model = monacoEditor.getModel();
      if (model) {
        monaco.editor.setModelLanguage(model, language.value);
      }

      // Set value and compute adaptive height
      monacoEditor.setValue(value || "");
      editorHeight.value = computeEditorHeight(value || "");

      // Move editor from hidden container into the visible modal area
      if (persistentContainer && editContainerRef.value) {
        if (persistentContainer.parentElement !== editContainerRef.value) {
          editContainerRef.value.appendChild(persistentContainer);
        }
        persistentContainer.style.position = "relative";
        persistentContainer.style.top = "0";
        persistentContainer.style.pointerEvents = "auto";
        persistentContainer.style.width = "100%";
        persistentContainer.style.height = "100%";
        monacoEditor.layout();
      }
    }

    watch(
      () => visible.value,
      (bool) => {
        if (!bool) {
          emit("close");
          // Hide editor back — don't dispose, just move off-screen
          if (persistentContainer) {
            persistentContainer.style.position = "fixed";
            persistentContainer.style.top = "-9999px";
            persistentContainer.style.pointerEvents = "none";
            if (persistentContainer.parentElement !== document.body) {
              document.body.appendChild(persistentContainer);
            }
          }
        }
      }
    );

    function setMonacoEditorValue(dataValue) {
      if (monacoEditor) {
        monacoEditor.setValue(dataValue);
      }
    }

    function handleOk() {
      if (monacoEditor) {
        emit("oks", monacoEditor.getValue(), currentType);
      }
      visible.value = false;
    }

    onUnmounted(() => {
      if (monacoEditor) {
        monacoEditor.dispose();
        monacoEditor = null;
        editorReady = false;
      }
      if (persistentContainer && persistentContainer.parentElement) {
        persistentContainer.parentElement.removeChild(persistentContainer);
        persistentContainer = null;
      }
    });

    return {
      visible,
      handleOk,
      setMonacoEditorValue,
      init,
      editorHeight,
      editContainerRef,
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
      overflow: hidden;
    }
  }
}
</style>