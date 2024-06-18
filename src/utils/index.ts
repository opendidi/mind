/*
 * @Descripttion:
 * @version: 1.0.0
 * @Author: htang
 * @Date: 2023-09-14 08:50:34
 * @LastEditors: htang
 * @LastEditTime: 2023-11-28 18:01:40
 */

export enum EventAction {
  Link,           // 打开链接
  SetProps,       // 更改属性
  StartAnimate,   // 执行动画
  PauseAnimate,   // 暂停动画
  StopAnimate,    // 停止动画
  JS,             // 执行JS代码
  GlobalFn,       // 执行全局函数
  Emit,           // 发送消息
  StartVideo,     // 播放视频
  PauseVideo,     // 暂停视频
  StopVideo,      // 停止视频
  SendPropData,   // 发送图元数据
  SendVarData,    // 发送绑定变量
}

export enum LOCK_STATE_DATA {
  // 0 -未锁定
  None,
  // 1 - 禁止编辑，隐藏大小、缩放、选中编辑框；可选中、高亮、移动、触发事件等
  DisableEdit,
  // 2 - 禁止编辑 + 移动；可选中、高亮、触发事件等
  DisableMove,
  // 3 - 禁止缩放（1.2.14版本以后）
  DisableScale,
  // 4 - 禁止移动和缩放（1.2.14版本以后）
  DisableMoveScale,
  // 10 - 不触发任何操作和事件
  Disable = 10,
}

// pen 类型。0 - node；1 - line
export enum PEN_TYPE {
  // 节点
  Node,
  // 连线
  Line,
}

export enum GRADIENT {
  None,   // 没有渐变
  Linear, // 线性渐变
  Radial, // 发散渐变
}