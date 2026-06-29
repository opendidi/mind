<template>
  <Teleport to="body">
    <transition name="lightbox-fade">
      <div v-if="src" class="lightbox-overlay" @click="close">
        <img :src="src" class="lightbox-img" @click.stop />
        <span class="lightbox-close" @click="close">&times;</span>
      </div>
    </transition>
  </Teleport>
</template>

<script setup lang="ts">
const props = defineProps<{ src: string }>()
const emit = defineEmits<{ close: [] }>()

function close() {
  emit('close')
}
</script>

<style lang="scss" scoped>
.lightbox-overlay {
  position: fixed;
  inset: 0;
  z-index: 2000;
  background: rgba(0, 0, 0, 0.72);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  .lightbox-img {
    max-width: 90vw;
    max-height: 90vh;
    border-radius: 8px;
    box-shadow: 0 8px 40px rgba(0, 0, 0, 0.3);
    cursor: default;
  }
  .lightbox-close {
    position: absolute;
    top: 16px;
    right: 20px;
    width: 36px;
    height: 36px;
    border-radius: 50%;
    background: rgba(255, 255, 255, 0.15);
    color: #fff;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 18px;
    cursor: pointer;
    transition: background 0.15s;
    &:hover {
      background: rgba(255, 255, 255, 0.25);
    }
  }
}

.lightbox-fade-enter-active,
.lightbox-fade-leave-active {
  transition: opacity 0.2s ease;
}
.lightbox-fade-enter-from,
.lightbox-fade-leave-to {
  opacity: 0;
}
</style>
