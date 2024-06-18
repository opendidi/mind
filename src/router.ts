/*
 * @Descripttion:
 * @version: 1.0.0
 * @Author: htang
 * @Date: 2024-04-01 16:25:43
 * @LastEditors: htang
 * @LastEditTime: 2024-04-01 17:51:02
 */
import { createRouter, createWebHistory } from 'vue-router';

const routes = [
  { path: '/', component: () => import('./views/Index.vue') },
  { path: '/preview', component: () => import('./views/Preview.vue') },
];

const router = createRouter({
  history: createWebHistory(import.meta.env.VITE_PUBLIC_PATH),
  routes,
});

export default router;