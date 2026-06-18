/*
 * @Descripttion:
 * @version: 1.0.0
 * @Author: htang
 * @Date: 2023-10-10 10:47:09
 * @LastEditors: htang
 * @LastEditTime: 2025-08-26 14:56:53
 */
import { defineStore } from 'pinia';
import { store } from '@/store';
import { getTopology, getIsSave, setIsSave, getVariableData, setVariableData } from '@/utils/meta-storage'
import { getGraphicGroups, setGraphicGroups } from '@/utils/graphicGroups'

export const useCommonStore = defineStore('common', {
  state: () => ({
    topology: getTopology() || {},
    graphics: getGraphicGroups() || {},
    isSave: getIsSave() || '1',
    variableData: getVariableData() || [],
    customFolders: JSON.parse(localStorage.getItem('custom_folders') || 'null') || [],
  }),
  actions: {
    setTopology(data) {
      this.topology = data;
    },
    setGraphicGroups(data) {
      this.graphics = data;
      setGraphicGroups(JSON.stringify(data));
    },
    setIsSave(data) {
      this.isSave = data;
      setIsSave(data);
    },
    setVariableData(data) {
      this.variableData = data;
      setVariableData(data);
    },
    setCustomFolders(data) {
      this.customFolders = data;
      localStorage.setItem('custom_folders', JSON.stringify(data));
    }
  }
})

// Need to be used outside the setup
export function useCommonStoreWithOut() {
  return useCommonStore(store);
}