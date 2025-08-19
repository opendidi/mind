<!--
 * @Descripttion:
 * @version: 1.0.0
 * @Author: htang
 * @Date: 2023-09-11 08:50:37
 * @LastEditors: htang
 * @LastEditTime: 2025-08-19 15:33:31
-->
<template>
  <a-config-provider :locale="locale">
    <router-view />
  </a-config-provider>
</template>

<script setup>
import { ref } from "vue";
import zhCN from "ant-design-vue/es/locale/zh_CN";
const locale = ref(zhCN);
</script>