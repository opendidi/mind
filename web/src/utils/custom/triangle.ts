/*
 * @Descripttion:
 * @version: 1.0.0
 * @Author: htang
 * @Date: 2023-11-22 14:32:06
 * @LastEditors: htang
 * @LastEditTime: 2023-11-22 15:45:52
 */
import { Pen } from "@meta2d/core";

// 1. 编写图形绘画函数
// 其中，calculative.worldRect为canvas的世界坐标。更多信息，参考 “架构” - “概要” 和 Pen 相关文档
export function triangle(ctx: CanvasRenderingContext2D, pen: Pen): void {
  // 在绘画中若更改了 ctx 的某个属性，例如：fillStyle, strokeStyle, lineWidth 等样式属性，需使用 save 和 restore
  // 注意 save restore 需要成对调用
  // ctx.save();
  // 若在绘画函数中，配置了 ctx.strokeStyle or fillStyle ，那么画笔的 color or background 无法对它生效
  // ctx.strokeStyle = '#1890ff';
  ctx.moveTo(pen.calculative.worldRect.x + pen.calculative.worldRect.width / 2, pen.calculative.worldRect.y);

  ctx.lineTo(
    pen.calculative.worldRect.x + pen.calculative.worldRect.width,
    pen.calculative.worldRect.y + pen.calculative.worldRect.height
  );

  ctx.lineTo(pen.calculative.worldRect.x, pen.calculative.worldRect.y + pen.calculative.worldRect.height);

  ctx.lineTo(pen.calculative.worldRect.x + pen.calculative.worldRect.width / 2, pen.calculative.worldRect.y);

  ctx.closePath();
  ctx.stroke();

  ctx.beginPath()
  ctx.arc(pen.calculative.worldRect.x + pen.calculative.worldRect.width / 2, pen.calculative.worldRect.y - 50, 6, 0, 2 * Math.PI, true);

  ctx.closePath();
  ctx.stroke();
  // 若需要填充 ctx.fill();

  // ctx.restore();
}

// 2. 如果需要，编写锚点函数。通常，可以使用默认锚点，然后通过快捷键动态添加锚点
// 注意，锚点左边为相对宽高的百分比小数（0-1之间的小数）
export function triangleAnchors(pen: Pen) {
  const anchors: Point[] = [];
  anchors.push({
    id: '0',
    penId: pen.id,
    x: 0.5,
    y: 0,
  });

  anchors.push({
    id: '1',
    penId: pen.id,
    x: 1,
    y: 1,
  });

  anchors.push({
    id: '2',
    penId: pen.id,
    x: 0,
    y: 1,
  });

  pen.anchors = anchors;
}