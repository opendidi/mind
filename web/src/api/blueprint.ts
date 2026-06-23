import http from '@/utils/request'

const API = {
  lists: '/blueprint/lists',
  find: '/blueprint/find',
  add: '/blueprint/add',
  modify: '/blueprint/modify',
  delete: '/blueprint/delete',
}

export function apiBlueprintList(params: Record<string, unknown>) {
  return http.get(API.lists, { params }).then((res: any) => res.data)
}

export function apiBlueprintFind(params: Record<string, unknown>) {
  return http.get(API.find, { params }).then((res: any) => res)
}

export function apiBlueprintAdd(data: Record<string, unknown>) {
  return http.post(API.add, data).then((res: any) => res.data)
}

export function apiBlueprintModify(data: Record<string, unknown>) {
  return http.post(API.modify, data).then((res: any) => res)
}

export function apiBlueprintDelete(data: Record<string, unknown>) {
  return http.post(API.delete, data).then((res: any) => res)
}
