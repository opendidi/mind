/*
 * @Descripttion:
 * @version: 1.0.0
 * @Author: htang
 * @Date: 2024-09-24 16:41:18
 * @LastEditors: htang
 * @LastEditTime: 2025-08-15 10:40:55
 */
import http from '@/utils/request'

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
 */
export function apiMaterialList(params: any) {
  return http.get(API.lists, { params })
}

/**
 * 获取所有目录数据
 */
export function apiMaterialFolder(params: any) {
  return http.get(API.folder, { params })
}

/**
 * 创建目录
 */
export function apiMaterialCreatedFolder(data: any) {
  return http.post(API.created, data, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

/**
 * 剪切文件
 */
export function apiMaterialScissors(data: any) {
  return http.post(API.scissors, data, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

/**
 * 复制文件
 */
export function apiMaterialCopy(data: any) {
  return http.post(API.copy, data, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

/**
 * 删除素材文件数据
 */
export function apiMaterialDelete(data: any) {
  return http.post(API.delete, data, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

/**
 * 修改素材文件数据
 */
export function apiMaterialModify(data: any) {
  return http.post(API.modify, data, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}
