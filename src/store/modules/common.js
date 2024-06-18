/*
 * @Descripttion:
 * @version: 1.0.0
 * @Author: htang
 * @Date: 2023-10-10 10:47:09
 * @LastEditors: htang
 * @LastEditTime: 2023-10-12 20:51:00
 */
import { defineStore } from 'pinia';
import { store } from '@/store';
import { getTopology } from '@/utils/meta-storage'
import { getGraphicGroups, setGraphicGroups } from '@/utils/graphicGroups'

export const useCommonStore = defineStore('common', {
  state: () => ({
    topology: getTopology() || {},
    graphics: getGraphicGroups() || {},
  }),
  getters: {
    getTopology(state) {
      return state.topology || {};
    },
    getGraphicGroups(state) {
      return state.graphics || {};
    }
  },
  actions: {
    setTopology(data) {
      this.topology = data;
    },
    setGraphicGroups(data) {
      this.graphics = data;
      setGraphicGroups(JSON.stringify(data));
    }
  }
})

// Need to be used outside the setup
export function useCommonStoreWithOut() {
  return useCommonStore(store);
}