/*
 * @Descripttion:
 * @version: 1.0.0
 * @Author: htang
 * @Date: 2026-06-17 09:28:01
 * @LastEditors: htang
 * @LastEditTime: 2026-06-18 09:32:44
 */
import { createRouter, createWebHistory } from 'vue-router';
import Layout from '@/layout/index.vue';

const routes = [
  {
    path: '/',
    component: Layout,
    redirect: '/',
    children: [
      { path: '/', component: () => import('@/views/Index.vue'), meta: { title: 'Mind' } },
      { path: '/preview/:id', component: () => import('@/views/Preview.vue'), meta: { title: '预览' } },
      { path: '/chat/:id?', name: 'chat', component: () => import('@/views/chat/index.vue'), meta: { title: 'AI 对话' } },
      { path: '/profile', name: 'profile', component: () => import('@/views/user/profile.vue'), meta: { title: '个人中心' } },
      { path: '/:id', component: () => import('@/views/Index.vue'), meta: { title: 'Mind' } },
    ],
  },
  { path: '/login', name: 'login', component: () => import('@/views/user/login.vue'), meta: { title: '登录' } },
  { path: '/register', name: 'register', component: () => import('@/views/user/register.vue'), meta: { title: '注册' } },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

export default router;