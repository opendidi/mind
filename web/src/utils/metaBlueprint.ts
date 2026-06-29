import type { Meta2d } from '@meta2d/core'

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
    gridSize: bp.gridSize || '',
    gridRotate: bp.gridRotate || '',
    rule: bp.rule === '1' || bp.rule === true || undefined,
    ruleColor: bp.ruleColor || '',
    initJs: bp.initJs || '',
    https: bp.https || [],
    thumbnail: bp.thumbnail || '',
    locked: 0,
  })
  meta2d.store.data.fromArrow = ''
  meta2d.store.data.toArrow = 'triangleSolid'
}
