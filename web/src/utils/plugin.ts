/*
 * @Descripttion:
 * @version: 1.0.0
 * @Author: htang
 * @Date: 2024-04-03 21:02:08
 * @LastEditors: htang
 * @LastEditTime: 2024-04-03 21:17:51
 */
import { mindBoxPlugin } from "@meta2d/plugin-mind-core";
import { collapseChildPlugin } from "@meta2d/plugin-mind-collapse"

export class MetaPlugin {

  editor: any;

  constructor(editor: any) {
    this.editor = editor;
  }

  /**
   * 初始化插件
   * @param {*} meta2d
   * @param {*} target 目标组件
   * @param {*} options 配置信息
   */
  initPlugin(meta2d: any, target: string, options: any = {}) {
    meta2d.installPenPlugins({ name: target }, [{
      plugin: mindBoxPlugin,
      options,
    }, {
      plugin: collapseChildPlugin,
      options,
    }])
  }

}