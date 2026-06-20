/**
 * 应用入口 — 全局初始化
 * UI 库：Ant Design Vue（主力）+ TDesign Vue Next（仅 <t-icon> / ColorPicker）
 */
import 'virtual:windi-base.css';
import 'virtual:windi-components.css';
import 'virtual:windi-utilities.css';
// ant-design-vue CSS: 全局样式（保留以覆盖动态创建的组件） + unplugin-vue-components 按需注入
// 纯 tree-shaking 会导致编辑器等程序化创建的组件丢失样式，保留全局 CSS 作为安全兜底
import 'ant-design-vue/dist/antd.css';
import '@/assets/icon/iconfont.css';
import '@/assets/styles/theme.css';

import { createApp } from 'vue';
import App from './App.vue';
import router from './router';
import { setupStore } from '@/store';
import Antd from 'ant-design-vue';
import TDesign from 'tdesign-vue-next';
import './permission';

// 运行时脚本（Meta2D 依赖）
import '@/assets/js/assets.le5lecdn.com_2d_canvas2svg.js';
import '@/assets/js/font_4042197_vr5c62twlzh.js';

// Monaco Editor worker 一次性初始化（Vite ?worker 后缀 → 独立 chunk）
import TsWorker from 'monaco-editor/esm/vs/language/typescript/ts.worker?worker';
import JsonWorker from 'monaco-editor/esm/vs/language/json/json.worker?worker';
import CssWorker from 'monaco-editor/esm/vs/language/css/css.worker?worker';
import HtmlWorker from 'monaco-editor/esm/vs/language/html/html.worker?worker';
import EditorWorker from 'monaco-editor/esm/vs/editor/editor.worker?worker';

self.MonacoEnvironment = {
  getWorker(_: string, label: string) {
    if (label === 'json') return new JsonWorker();
    if (label === 'css' || label === 'scss' || label === 'less') return new CssWorker();
    if (label === 'html' || label === 'handlebars' || label === 'razor') return new HtmlWorker();
    if (label === 'typescript' || label === 'javascript') return new TsWorker();
    return new EditorWorker();
  },
};

// DEV: Windi CSS 开发工具
if (import.meta.env.DEV) {
  import('virtual:windi-devtools');
}

const app = createApp(App);
app.use(router).use(Antd).use(TDesign);
setupStore(app);
app.mount('#app');