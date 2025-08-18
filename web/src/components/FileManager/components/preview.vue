<!--
 * @Descripttion:
 * @version: 1.0.0
 * @Author: htang
 * @Date: 2025-07-09 14:19:33
 * @LastEditors: htang
 * @LastEditTime: 2025-08-18 17:26:14
-->
<template>
  <div></div>
</template>

<script>
import {
  ref,
  watch,
  defineComponent,
  getCurrentInstance,
  onMounted,
  onUnmounted,
} from "vue";
import PhotoSwipeLightbox from "photoswipe/lightbox";
import "photoswipe/style.css";

export default defineComponent({
  setup() {
    let lightbox = null;

    onMounted(() => {
      lightbox = new PhotoSwipeLightbox({
        gallery: "#gallery",
        children: "a",
        pswpModule: () => import("photoswipe"),
      });
      lightbox.init();
    });

    /**
     * 预览图片
     */
    const openPreview = (record) => {
      // 动态创建一个 a 标签来传递图片数据给 PhotoSwipeLightbox
      const galleryElement = document.createElement("div");
      galleryElement.id = "gallery";
      galleryElement.innerHTML = `<a href="${record.url}" data-pswp-width="${record.width}" data-pswp-height="${record.height}" target="_blank"></a>`;

      // 将 a 标签添加到 DOM 中
      document.body.appendChild(galleryElement);

      // 使用 Lightbox 打开图片
      lightbox.loadAndOpen(0);

      // 清理临时元素
      setTimeout(() => {
        document.body.removeChild(galleryElement);
      }, 1000);
    };

    onUnmounted(() => {
      if (lightbox) {
        lightbox.destroy();
        lightbox = null;
      }
    });

    return {
      openPreview,
    };
  },
});
</script>

<style lang="less" scoped>
.pswp__bg {
  background: rgba(0, 0, 0, 0.85);
}
</style>