/*
 * @Descripttion:
 * @version: 1.0.0
 * @Author: htang
 * @Date: 2023-11-05 00:39:23
 * @LastEditors: htang
 * @LastEditTime: 2025-08-21 20:28:38
 */
const KEY: string = 'meta2d';
const ORIGINAL_KEY: string = 'original_meta2d';
const VARILE_DATA = 'variableData_meta2d'
const GRAPHIC_KEY: string = 'meta2d-graphic-groups';

export function getTopology() {
  return localStorage.getItem(KEY)
}

export function setTopology(token) {
  return localStorage.setItem(KEY, token)
}

export function removeTopology() {
  return localStorage.removeItem(KEY)
}

export function getOriginalData() {
  return localStorage.getItem(ORIGINAL_KEY)
}

export function setOriginalData(data) {
  return localStorage.setItem(ORIGINAL_KEY, data)
}

export function removeOriginalData() {
  return localStorage.removeItem(ORIGINAL_KEY)
}

export function getVariableData() {
  return localStorage.getItem(VARILE_DATA)
}

export function setVariableData(data) {
  return localStorage.setItem(VARILE_DATA, JSON.stringify(data))
}

export function removeVariableData() {
  return localStorage.removeItem(VARILE_DATA)
}

export function getGraphicGroups() {
  let data: any = localStorage.getItem(GRAPHIC_KEY);
  if (data) {
    return JSON.parse(data);
  } else {
    return {}
  }
}

export function setGraphicGroups(data: any) {
  return localStorage.setItem(GRAPHIC_KEY, JSON.stringify(data))
}

export function removeGraphicGroups() {
  return localStorage.removeItem(GRAPHIC_KEY)
}

export function setIsSave(isSave: any) {
  return localStorage.setItem('isSave', isSave)
}

export function getIsSave() {
  return localStorage.getItem('isSave')
}

export function removeIsSave() {
  return localStorage.removeItem('isSave')
}