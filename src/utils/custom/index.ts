/*
 * @Descripttion:
 * @version: 1.0.0
 * @Author: htang
 * @Date: 2023-11-22 15:10:50
 * @LastEditors: htang
 * @LastEditTime: 2023-11-22 15:29:36
 */
import { triangle, triangleAnchors } from "@/utils/custom/triangle";

export default async function initCustom() {
  // 3. 注册图形
  // 参数 {key: fn}。key为图形唯一name，否则覆盖原来图形，fn为相关函数
  await meta2d.registerCanvasDraw({ triangleNew: triangle });
  await meta2d.registerAnchors({ triangleNew: triangleAnchors });
}