import { inject, provide, type InjectionKey } from 'vue'
import type { Meta2d } from '@meta2d/core'

export const CanvasKey: InjectionKey<Meta2d> = Symbol('meta2d-canvas')

export function provideCanvas(meta2d: Meta2d) {
  provide(CanvasKey, meta2d)
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  ;(window as any).meta2d = meta2d // backward compatibility
}

export function useCanvas(): Meta2d {
  const meta2d = inject(CanvasKey)
  if (!meta2d) {
    console.warn('useCanvas: falling back to window.meta2d')
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    return (window as any).meta2d
  }
  return meta2d
}
