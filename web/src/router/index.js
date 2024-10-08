import { createRouter, createWebHashHistory, createWebHistory } from 'vue-router';

const routes = [
  { path: '/', component: () => import('@/views/Index.vue') },
  { path: '/preview', component: () => import('@/views/Preview.vue') },
];

const router = createRouter({
  history: createWebHashHistory(),
  routes,
});

export default router;