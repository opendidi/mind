/*
 * @Descripttion:
 * @version: 1.0.0
 * @Author: htang
 * @Date: 2024-01-15 11:46:57
 * @LastEditors: htang
 * @LastEditTime: 2024-01-15 11:49:56
 */
import { EventAction as eventAction } from '@/utils/index.ts';

const EVENT_ACTION_TYPE = [{
  name: '鼠标进入',
  value: 'enter',
}, {
  name: '鼠标离开',
  value: 'leave',
}, {
  name: '选中',
  value: 'active',
}, {
  name: '取消选中',
  value: 'inactive',
}, {
  name: '单击',
  value: 'click',
}, {
  name: '双击',
  value: 'dblclick',
}, {
  name: '鼠标按下',
  value: 'mousedown',
}, {
  name: '鼠标抬起',
  value: 'mouseup',
}, {
  name: '值变化',
  value: 'valueUpdate',
}]

const EVENT_ACTION_LIST = [{
  name: '打开链接',
  value: eventAction.Link,
}, {
  name: '更改属性',
  value: eventAction.SetProps,
}, {
  name: '执行动画',
  value: eventAction.StartAnimate,
}, {
  name: '暂停动画',
  value: eventAction.PauseAnimate,
}, {
  name: '停止动画',
  value: eventAction.StopAnimate,
}, {
  name: '执行JS代码',
  value: eventAction.JS,
}, {
  name: '执行全局函数',
  value: eventAction.GlobalFn,
}, {
  name: '发送消息',
  value: eventAction.Emit,
}, {
  name: '播放视频',
  value: eventAction.StartVideo,
}, {
  name: '暂停视频',
  value: eventAction.PauseVideo,
}, {
  name: '停止视频',
  value: eventAction.StopVideo,
}, {
  name: '发送图元数据',
  value: eventAction.SendPropData,
}, {
  name: '发送绑定变量',
  value: eventAction.SendVarData,
}]

export {
  EVENT_ACTION_TYPE,
  EVENT_ACTION_LIST
}