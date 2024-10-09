import http from '@/utils/request';

const API = {
  lists: '/material/lists',
  folder: '/material/folder',
  created: '/material/created_folder',
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