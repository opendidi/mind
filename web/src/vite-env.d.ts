/// <reference types="vite/client" />

declare namespace NodeJS {
  interface ImportMeta {
    readonly env: ImportMetaEnv
  }
}

interface ImportMetaEnv {
  readonly VITE_GLOB_API_URL: string
  readonly VITE_APP_BASE_URL: string
  [key: string]: string | undefined
}
