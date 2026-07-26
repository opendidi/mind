/// <reference types="vite/client" />

declare module '*.vue' {
  import type { DefineComponent } from 'vue'
  const component: DefineComponent<object, object, unknown>
  export default component
}

// Allow importing legacy .js store modules
declare module '@/store/modules/common' {
  export function useCommonStore(): any
  export function useCommonStoreWithOut(): any
  export default useCommonStoreWithOut
}
