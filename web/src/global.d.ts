/*
 * @Descripttion:
 * @version: 1.0.0
 * @Author: htang
 * @Date: 2023-09-11 08:50:37
 * @LastEditors: htang
 * @LastEditTime: 2023-10-11 15:06:28
 */
import { Meta2d } from '@meta2d/core'

declare global {
  // eslint-disable-next-line no-var
  var meta2d: Meta2d

  // eslint-disable-next-line no-var
  var C2S: any
}

// Augment Meta2d for practical usage — Meta2D's types have deep recursive
// circular references that cause TS2322/TS18046 errors in consumer code.
declare module '@meta2d/core' {
  interface Meta2d {
    [key: string]: any
  }
  interface Pen {
    [key: string]: any
  }
}
