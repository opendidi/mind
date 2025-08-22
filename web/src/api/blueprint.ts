/*
 * @Descripttion:
 * @version: 1.0.0
 * @Author: htang
 * @Date: 2025-08-22 14:57:15
 * @LastEditors: htang
 * @LastEditTime: 2025-08-22 15:06:09
 */
import http from '@/utils/request';

const API = {
  lists: '/material/lists',
  find: '/material/find',
  add: '/material/add',
  modify: '/material/modify',
  delete: '/material/delete',
}

/**
 * 获取图纸列表
 * @param data
 * @returns
 */
export function apiBlueprintList(params: any) {
  return new Promise(async (resolve, reject) => {
    await http.get(API.lists, { params }).then((res: any) => {
      resolve(res);
    })
  })
}

/**
 * 根据ID获取图纸详情
 * @param data
 * @returns
 */
export function apiBlueprintFind(params: any) {
  return new Promise(async (resolve, reject) => {
    await http.get(API.find, { params }).then((res: any) => {
      resolve(res);
    })
  })
}

/**
 * 新增图纸
 * @param params
 * @returns
 */
export function apiBlueprintAdd(data: any) {
  return new Promise(async (resolve, reject) => {
    await http.post(API.add, data, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    }).then((res: any) => {
      resolve(res);
    })
  })
}

/**
 * 编辑图纸
 * @param params
 * @returns
 */
export function apiBlueprintModify(data: any) {
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

/**
 * 删除图纸
 * @param params
 * @returns
 */
export function apiBlueprintDelete(data: any) {
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