/*
 * @Descripttion:
 * @version: 1.0.0
 * @Author: htang
 * @Date: 2026-06-17 08:49:24
 * @LastEditors: htang
 * @LastEditTime: 2026-06-26 10:20:48
 */
/*
 * @Descripttion:
 * @version: 1.0.0
 * @Author: htang
 * @Date: 2023-09-11 08:50:37
 * @LastEditors: htang
 * @LastEditTime: 2025-08-19 17:39:33
 */
import { defineConfig, ConfigEnv, loadEnv } from 'vite';
import vue from '@vitejs/plugin-vue';
import UnoCSS from 'unocss/vite';
import Components from 'unplugin-vue-components/vite';
import { AntDesignVueResolver } from 'unplugin-vue-components/resolvers';
import { OUTPUT_DIR } from './build/constant';
import * as path from 'path';
import { createProxy } from './build/vite/proxy';
import { wrapperEnv } from './build/utils';
import { resolve } from 'path';

function pathResolve(dir: string) {
  return resolve(process.cwd(), '.', dir);
}

const TimeStamp = new Date().getTime();

// https://vitejs.dev/config/
export default ({ command, mode }: ConfigEnv) => {
  const env = loadEnv(mode, process.cwd());
  const root = process.cwd();
  const isBuild = command === 'build';
  const viteEnv = wrapperEnv(env);
  const { VITE_PORT, VITE_PROXY } = viteEnv;
  return defineConfig({
    base: env.VITE_APP_BASE_URL,
    root,
    plugins: [
      vue(),
      UnoCSS(),
      Components({
        resolvers: [
          AntDesignVueResolver({
            importStyle: 'less',
            resolveIcons: true,
          }),
        ],
        dts: 'src/components.d.ts',
      }),
    ],
    server: {
      host: true,
      https: false,
      port: VITE_PORT,
      proxy: createProxy(VITE_PROXY),
    },
    css: {
      preprocessorOptions: {
        scss: {
          api: 'modern',
        },
        less: {
          modifyVars: {
            hack: `true; @import (reference) "${path.resolve("src/assets/css/base.less")}";`,
          },
          javascriptEnabled: true,
        },
      },
      devSourcemap: true,
    },
    resolve: {
      alias: [
        {
          find: /\/@\//,
          replacement: pathResolve('src') + '/',
        },
        {
          find: /\/#\//,
          replacement: pathResolve('types') + '/',
        },
        {
          find: /@\//,
          replacement: pathResolve('src') + '/',
        },
        {
          find: /#\//,
          replacement: pathResolve('types') + '/',
        },
      ],
    },
    esbuild: {
      drop: isBuild ? ['console', 'debugger'] : [],
    },
    build: {
      minify: 'esbuild',
      target: 'es2020',
      cssTarget: 'chrome80',
      outDir: OUTPUT_DIR,
      reportCompressedSize: false,
      chunkSizeWarningLimit: 2000,
      cssCodeSplit: true,
      rollupOptions: {
        output: {
          manualChunks: {
            'monaco-editor': ['monaco-editor'],
            echarts: ['echarts'],
            antd: ['ant-design-vue', '@ant-design/icons-vue'],
            tdesign: ['tdesign-vue-next', 'tdesign-icons-vue-next'],
            meta2d: ['@meta2d/core'],
            markmap: ['markmap-lib', 'markmap-view'],
            vendor: ['vue', 'vue-router', 'pinia', 'axios'],
          },
          entryFileNames: `assets/[name]-${TimeStamp}.js`,
          chunkFileNames: `assets/[name]-[hash]-${TimeStamp}.js`,
          assetFileNames: `assets/[name]-[hash]-${TimeStamp}.[ext]`,
        },
      },
    },
    optimizeDeps: {
      esbuildOptions: {
        target: 'es2020',
      },
      include: [
        'ant-design-vue/es/locale/zh_CN',
        'ant-design-vue/es/locale/en_US',
        'monaco-editor',
      ],
    },
  });
};
