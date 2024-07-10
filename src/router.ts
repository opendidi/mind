/*
 * @Descripttion:
 * @version: 1.0.0
 * @Author: htang
 * @Date: 2024-04-01 16:25:43
 * @LastEditors: htang
 * @LastEditTime: 2024-07-10 14:10:08
 */
import { createRouter, createWebHashHistory, createWebHistory } from 'vue-router';

const routes = [
  { path: '/', component: () => import('./views/Index.vue') },
  { path: '/preview', component: () => import('./views/Preview.vue') },
];

const router = createRouter({
  history: createWebHashHistory(),
  routes,
});

export default router;