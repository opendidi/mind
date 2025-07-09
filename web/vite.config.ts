/*
 * @Descripttion:
 * @version: 1.0.0
 * @Author: htang
 * @Date: 2023-09-11 08:50:37
 * @LastEditors: htang
 * @LastEditTime: 2025-07-09 14:26:29
 */
import { defineConfig, UserConfig, ConfigEnv, loadEnv } from 'vite';
import vue from '@vitejs/plugin-vue';
import windiCSS from 'vite-plugin-windicss';
import { OUTPUT_DIR } from './build/constant';
import * as path from 'path';
import { createProxy } from './build/vite/proxy';
import { wrapperEnv } from './build/utils';

const TimeStamp = new Date().getTime();

// https://vitejs.dev/config/
export default ({ command, mode }: ConfigEnv): UserConfig => {
  const env = loadEnv(mode, process.cwd());
  const root = process.cwd();
  const isBuild = command === 'build';
  const viteEnv = wrapperEnv(env);
  const { VITE_PORT, VITE_PUBLIC_PATH, VITE_PROXY } = viteEnv;
  return defineConfig({
    // 参考：https://www.jianshu.com/p/4973bd983e96
    base: env.VITE_APP_BASE_URL,
    root,
    envDir: 'env',
    plugins: [vue(), windiCSS()],
    server: {
      // Listening on all local IPs
      host: true,
      https: false,
      port: VITE_PORT,
      // Load proxy configuration from .env
      proxy: createProxy(VITE_PROXY),
    },
    css: {
      preprocessorOptions: {
        less: {
          modifyVars: {
            hack: `true; @import (reference) "${path.resolve("src/assets/css/base.less")}";`,
          },
          javascriptEnabled: true,
        },
      },
    },
    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src/'),
      },
    },
    esbuild: {
      //清除全局的console.log和debug
      drop: isBuild ? ['console', 'debugger'] : [],
    },
    build: {
      minify: 'esbuild',
      target: 'es2015',
      cssTarget: 'chrome80',
      outDir: OUTPUT_DIR,
      terserOptions: {
        compress: {
          // keep_infinity: true,
          // // Used to delete console in production environment
          // drop_console: VITE_DROP_CONSOLE,
          // drop_debugger: true,
        },
      },
      // Turning off brotliSize display can slightly reduce packaging time
      reportCompressedSize: false,
      chunkSizeWarningLimit: 2000,
      rollupOptions: {
        // 参考：https://blog.cinob.cn/archives/393
        output: {
          // 入口文件名
          entryFileNames: `assets/[name]-${TimeStamp}.js`,
          // 块文件名
          chunkFileNames: `assets/[name]-[hash]-${TimeStamp}.js`,
          // 资源文件名 css 图片等等
          assetFileNames: `assets/[name]-[hash]-balabala-${TimeStamp}.[ext]`,
        }
      }
    },
  })
};