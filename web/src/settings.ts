/*
 * @Descripttion:
 * @version: 1.0.0
 * @Author: htang
 * @Date: 2024-10-08 20:11:25
 * @LastEditors: htang
 * @LastEditTime: 2024-10-09 15:58:43
 */
import { getConfigFileName } from '../build/getConfigFileName';

const ENV_NAME = getConfigFileName(import.meta.env);

const ENV = (import.meta.env.DEV
  ? // Get the global configuration (the configuration will be extracted independently when packaging)
  (import.meta.env as unknown)
  : window[ENV_NAME as any]) as unknown;

const {
  VITE_GLOB_APP_TITLE
} = ENV;

export default {
  title: VITE_GLOB_APP_TITLE,
}