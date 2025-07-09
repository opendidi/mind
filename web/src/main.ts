/*
 * @Descripttion:
 * @version: 1.0.0
 * @Author: htang
 * @Date: 2023-09-11 08:50:37
 * @LastEditors: htang
 * @LastEditTime: 2025-07-09 15:00:57
 */
import 'virtual:windi-base.css';
import 'virtual:windi-components.css';
import 'virtual:windi-utilities.css';
import 'virtual:windi-devtools';
import { createApp } from 'vue';
import App from './App.vue';

import router from "./router"
import TDesign from 'tdesign-vue-next';

import Antd from 'ant-design-vue';
import 'ant-design-vue/dist/antd.css';

import { setupStore } from '@/store';

import '@/assets/js/assets.le5lecdn.com_2d_canvas2svg.js'
import '@/assets/js/marked.min.js'
import '@/assets/js/font_4042197_vr5c62twlzh.js'

import '@/assets/icon/iconfont.css'

import './permission'

const app = createApp(App);

// 加载基础服务
app.use(router).use(Antd).use(TDesign);
// end

// 配置存储
setupStore(app);

app.mount('#app');