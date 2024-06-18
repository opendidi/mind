/*
 * @Descripttion:
 * @version: 1.0.0
 * @Author: htang
 * @Date: 2023-09-11 08:50:37
 * @LastEditors: htang
 * @LastEditTime: 2023-10-08 11:50:22
 */
import { Pen } from '@meta2d/core';
import { reactive } from 'vue';

export enum SelectionMode {
  File,
  Pen,
}

const selections = reactive<{
  mode: SelectionMode;
  pen?: Pen;
}>({
  // 选中对象类型：0 - 画布；1 - 单个图元
  mode: SelectionMode.File,
  pen: undefined,
});

export const useSelection = () => {
  const select = (pens?: Pen[]) => {
    if (!pens || pens.length !== 1) {
      selections.mode = SelectionMode.File;
      selections.pen = undefined;
      return;
    }

    selections.mode = SelectionMode.Pen;
    selections.pen = pens[0];
  };
  return {
    selections,
    select,
  };
};