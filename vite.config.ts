/*
 * @Descripttion:
 * @version: 1.0.0
 * @Author: htang
 * @Date: 2023-09-11 08:50:37
 * @LastEditors: htang
 * @LastEditTime: 2024-04-02 09:08:58
 */
import { defineConfig, loadEnv } from 'vite';
import vue from '@vitejs/plugin-vue';
import { OUTPUT_DIR } from './build/constant';
import * as path from 'path';

const TimeStamp = new Date().getTime();

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, 'env');
  return {
    // 参考：https://www.jianshu.com/p/4973bd983e96
    base: loadEnv(mode, process.cwd()).VITE_PUBLIC_PATH,
    plugins: [vue()],
    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src/'),
      },
    },
    server: {
      // Listening on all local IPs
      host: true,
      https: false,
      port: 5173,
      // Load proxy configuration from .env
      // proxy: createProxy(VITE_PROXY),
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
    envDir: 'env',
  }
});