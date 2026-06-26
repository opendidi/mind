import { defineConfig, presetUno } from 'unocss'

export default defineConfig({
  presets: [presetUno()],
  // shortcut to avoid collision with Ant Design / TDesign classes
  rules: [],
  shortcuts: {},
})
