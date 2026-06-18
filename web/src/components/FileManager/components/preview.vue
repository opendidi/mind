<!--
 * @Descripttion:
 * @version: 1.0.0
 * @Author: htang
 * @Date: 2025-07-09 14:19:33
 * @LastEditors: htang
 * @LastEditTime: 2026-06-18 09:10:58
-->
<template>
  <a-modal
    v-model:visible="textPreviewVisible"
    :title="textPreviewTitle"
    width="80%"
    centered
    :footer="null"
    :destroyOnClose="true"
    wrapClassName="text-preview-modal"
  >
    <template v-if="textPreviewType === 'markdown'">
      <div v-html="renderedMarkdown" class="markdown-preview"></div>
    </template>
    <template v-else>
      <pre class="code-preview">
        <code>{{ textPreviewContent }}</code>
      </pre>
    </template>
  </a-modal>
</template>

<script>
import { ref, computed, defineComponent, onMounted, onUnmounted } from "vue";
import PhotoSwipeLightbox from "photoswipe/lightbox";
import MarkdownIt from "markdown-it";
import "photoswipe/style.css";

// Reuse the same markdown-it config as the chat view
const md = new MarkdownIt({
  html: false,
  linkify: true,
  typographer: true,
  breaks: true,
});

export default defineComponent({
  setup() {
    let lightbox = null;

    // Text/code/markdown preview state
    const textPreviewVisible = ref(false);
    const textPreviewContent = ref("");
    const textPreviewType = ref("text");
    const textPreviewTitle = ref("");

    const renderedMarkdown = computed(() => {
      if (textPreviewType.value === "markdown" && textPreviewContent.value) {
        return md.render(textPreviewContent.value);
      }
      return "";
    });

    onMounted(() => {
      lightbox = new PhotoSwipeLightbox({
        gallery: "#gallery",
        children: "a",
        pswpModule: () => import("photoswipe"),
      });
      lightbox.init();
    });

    /**
     * 预览图片 (PhotoSwipe lightbox)
     */
    const openPreview = (record) => {
      const galleryElement = document.createElement("div");
      galleryElement.id = "gallery";
      galleryElement.innerHTML = `<a href="${record.url}" data-pswp-width="${record.width}" data-pswp-height="${record.height}" target="_blank"></a>`;
      document.body.appendChild(galleryElement);
      lightbox.loadAndOpen(0);
      setTimeout(() => {
        document.body.removeChild(galleryElement);
      }, 1000);
    };

    /**
     * 预览文本/代码/Markdown
     * @param {Object} params - { content, type, title }
     */
    const openTextPreview = (params) => {
      textPreviewContent.value = params.content;
      textPreviewType.value = params.type;
      textPreviewTitle.value = params.title;
      textPreviewVisible.value = true;
    };

    onUnmounted(() => {
      if (lightbox) {
        lightbox.destroy();
        lightbox = null;
      }
    });

    return {
      openPreview,
      openTextPreview,
      textPreviewVisible,
      textPreviewContent,
      textPreviewType,
      textPreviewTitle,
      renderedMarkdown,
    };
  },
});
</script>

<style lang="less" scoped>
.pswp__bg {
  background: rgba(0, 0, 0, 0.85);
}

.markdown-preview {
  max-height: 70vh;
  overflow-y: auto;
  padding: 16px 24px;
  line-height: 1.7;
  color: #333;

  :deep(h1),
  :deep(h2),
  :deep(h3) {
    margin-top: 1.2em;
    margin-bottom: 0.6em;
  }
  :deep(pre) {
    background: #f5f5f5;
    padding: 12px 16px;
    border-radius: 4px;
    overflow-x: auto;
  }
  :deep(code) {
    background: #f0f0f0;
    padding: 2px 6px;
    border-radius: 3px;
    font-size: 0.9em;
  }
  :deep(pre code) {
    background: transparent;
    padding: 0;
  }
  :deep(table) {
    border-collapse: collapse;
    width: 100%;
  }
  :deep(th),
  :deep(td) {
    border: 1px solid #ddd;
    padding: 8px 12px;
    text-align: left;
  }
  :deep(blockquote) {
    border-left: 3px solid #18bc9c;
    margin: 0;
    padding: 4px 16px;
    color: #666;
  }
}

.code-preview {
  max-height: 70vh;
  overflow: auto;
  margin: 0;
  padding: 16px 24px;
  background: #1e1e1e;
  color: #d4d4d4;
  font-family: Consolas, Monaco, "Courier New", monospace;
  font-size: 13px;
  line-height: 1.6;
  border-radius: 4px;
  white-space: pre-wrap;
  word-break: break-all;

  code {
    background: transparent;
    padding: 0;
  }
}
</style>
