/*
 * @Descripttion:
 * @version: 1.0.0
 * @Author: htang
 * @Date: 2023-10-10 10:47:09
 * @LastEditors: htang
 * @LastEditTime: 2025-08-21 20:17:43
 */
import { defineStore } from 'pinia';
import { store } from '@/store';
import { getTopology, getIsSave, setIsSave } from '@/utils/meta-storage'
import { getGraphicGroups, setGraphicGroups } from '@/utils/graphicGroups'

export const useCommonStore = defineStore('common', {
  state: () => ({
    topology: getTopology() || {},
    graphics: getGraphicGroups() || {},
    isSave: getIsSave() || false,
  }),
  getters: {
    getTopology(state) {
      return state.topology || {};
    },
    getGraphicGroups(state) {
      return state.graphics || {};
    },
    getIsSave(state) {
      return state.isSave || false;
    }
  },
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
    }
  }
})

// Need to be used outside the setup
export function useCommonStoreWithOut() {
  return useCommonStore(store);
}