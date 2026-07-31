import type { Meta2d } from '@meta2d/core'

/** Generate a default blueprint name with timestamp for new canvases */
export function defaultBlueprintName(): string {
  const now = new Date()
  const pad = (n: number) => String(n).padStart(2, '0')
  const date = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`
  const time = `${pad(now.getHours())}${pad(now.getMinutes())}${pad(now.getSeconds())}`
  return `新图纸_${date}_${time}`
}

export interface BlueprintData {
  pens?: any[]
  name?: string
  color?: string
  penBackground?: string
  background?: string
  bkImage?: string
  grid?: string | boolean
  gridColor?: string
  gridSize?: string
  gridRotate?: string
  rule?: string | boolean
  ruleColor?: string
  initJs?: string
  https?: any
  thumbnail?: string
}

export function applyBlueprintData(meta2d: Meta2d, bp: BlueprintData) {
  meta2d.open({
    pens: bp.pens || [],
    name: bp.name || '',
    color: bp.color || '',
    penBackground: bp.penBackground || '',
    background: bp.background || '',
    bkImage: bp.bkImage || '',
    grid: bp.grid === '1' || bp.grid === true || undefined,
    gridColor: bp.gridColor || '',
    gridSize: (bp.gridSize || '') as any,
    gridRotate: (bp.gridRotate || '') as any,
    rule: bp.rule === '1' || bp.rule === true || undefined,
    ruleColor: bp.ruleColor || '',
    initJs: bp.initJs || '',
    https: bp.https || [],
    thumbnail: bp.thumbnail || '',
    locked: 0,
  } as any)
  meta2d.store.data.fromArrow = ''
  meta2d.store.data.toArrow = 'triangleSolid'
}
