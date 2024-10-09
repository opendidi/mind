/*
 * @Descripttion:
 * @version: 1.0.0
 * @Author: htang
 * @Date: 2024-05-13 20:30:45
 * @LastEditors: htang
 * @LastEditTime: 2024-10-09 10:23:08
 */
import axios from 'axios'
import { message } from 'ant-design-vue'

const instance = axios.create({
  baseURL: import.meta.env.VITE_GLOB_API_URL as string,
  timeout: 100000,
});

// 添加请求拦截器
instance.interceptors.request.use(function (config: any) {
  // 在发送请求之前做些什么
  return config;
}, function (error) {
  // 对请求错误做些什么
  return Promise.reject(error);
});

// 添加响应拦截器
instance.interceptors.response.use(function (response: any) {
  // 对响应数据做点什么
  let { code, msg } = response['data'];
  switch (code) {
    case 500:
      message.error(msg);
      return Promise.reject(new Error(msg));
    case 200:
      return response['data'];
  }
}, function (error) {
  // 对响应错误做点什么
  return Promise.reject(error);
});

export default instance;