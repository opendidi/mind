/*
 * @Descripttion:
 * @version: 1.0.0
 * @Author: htang
 * @Date: 2024-09-24 16:41:18
 * @LastEditors: htang
 * @LastEditTime: 2025-08-15 10:40:55
 */
import http from '@/utils/request';

const API = {
  lists: '/material/lists',
  folder: '/material/folder',
  copy: '/material/copy',
  scissors: '/material/scissors',
  created: '/material/create_dir',
  modify: '/material/modify',
  delete: '/material/delete',
}

/**
 * 文件素材列表
 * @param data
 * @returns
 */
export function apiMaterialList(params: any) {
  return new Promise(async (resolve, reject) => {
    await http.get(API.lists, { params }).then((res: any) => {
      resolve(res);
    })
  })
}

/**
 * 获取所有目录数据
 * @param params
 * @returns
 */
export function apiMaterialFolder(params: any) {
  return new Promise(async (resolve, reject) => {
    await http.get(API.folder, { params }).then((res: any) => {
      resolve(res);
    })
  })
}

/**
 * 获取所有目录数据
 * @param params
 * @returns
 */
export function apiMaterialCreatedFolder(data: any) {
  return new Promise(async (resolve, reject) => {
    await http.post(API.created, data, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    }).then((res: any) => {
      resolve(res);
    })
  })
}

/**
 * 剪切文件
 * @param {String} id 文件ID
 * @param {String} folder 父ID
 * @returns
 */
export function apiMaterialScissors(data: any) {
  return new Promise(async (resolve, reject) => {
    await http.post(API.scissors, data, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    }).then((res: any) => {
      resolve(res);
    })
  })
}

/**
 * 复制文件
 * @param {String} id 文件ID
 * @param {String} folder 父ID
 * @returns
 */
export function apiMaterialCopy(data: any) {
  return new Promise(async (resolve, reject) => {
    await http.post(API.copy, data, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    }).then((res: any) => {
      resolve(res);
    })
  })
}

/**
 * 删除素材文件数据
 * @param params
 * @returns
 */
export function apiMaterialDelete(data: any) {
  return new Promise(async (resolve, reject) => {
    await http.post(API.delete, data, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    }).then((res: any) => {
      resolve(res);
    })
  })
}

export function apiMaterialModify(data: any) {
  return new Promise(async (resolve, reject) => {
    await http.post(API.modify, data, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    }).then((res: any) => {
      resolve(res);
    })
  })
}