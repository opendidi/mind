import { inject, provide, type InjectionKey } from 'vue'
import type { Meta2d } from '@meta2d/core'

export const CanvasKey: InjectionKey<Meta2d> = Symbol('meta2d-canvas')

export function provideCanvas(meta2d: Meta2d) {
  provide(CanvasKey, meta2d)
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  ;(window as any).meta2d = meta2d // backward compatibility
}

// Proxy defers property access until the real Meta2d instance is available.
// Component setup() runs before Editor's onMounted, so inject/window.meta2d
// may both be undefined at call time. The Proxy resolves on each access instead.
export function useCanvas(): Meta2d {
  const injected = inject(CanvasKey, null)
  return new Proxy({} as Meta2d, {
    get(_t, prop) {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const m = injected || (window as any).meta2d
      if (!m) return undefined
      const v = (m as any)[prop]
      return typeof v === 'function' ? v.bind(m) : v
    },
  })
}
