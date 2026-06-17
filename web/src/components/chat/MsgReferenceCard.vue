<!-- Reference card — shows web_search result links below AI replies -->
<template>
  <div v-if="references && references.length > 0" class="msg-refs">
    <div class="refs-label">参考来源</div>
    <a-space wrap :size="[4, 4]">
      <a-tag v-for="(ref, idx) in references" :key="idx" color="blue">
        <a :href="ref.url" target="_blank" rel="noopener">
          {{ ref.title || ref.url }}
        </a>
      </a-tag>
    </a-space>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  references?: Array<{ title?: string; url: string }>
}>()
</script>

<style scoped>
.msg-refs {
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px dashed #e8e8e8;
}
.refs-label {
  font-size: 11px;
  color: #999;
  margin-bottom: 4px;
}
</style>
