/*
 * @Descripttion:
 * @version: 1.0.0
 * @Author: htang
 * @Date: 2023-10-10 10:32:10
 * @LastEditors: htang
 * @LastEditTime: 2023-10-10 10:34:45
 */
import type { App } from 'vue';
import { createPinia } from 'pinia';
const store = createPinia();

export function setupStore(app: App<Element>) {
  app.use(store);
}

export { store };