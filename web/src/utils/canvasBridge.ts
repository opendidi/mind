/**
 * canvasBridge — bridges Agent canvas tool calls to Meta2D API operations.
 *
 * When the Agent calls canvas tools (add_pen, add_line, delete_pen, etc.),
 * the backend returns success results containing the operation data.
 * This module executes the corresponding Meta2D operations on the frontend.
 *
 * All operations go through notifyCanvasMutation() to ensure:
 *   - localStorage is synced
 *   - Save state is marked dirty (isSave = '0')
 *   - Custom event dispatched for external listeners (e.g., Index.vue save pipeline)
 */

export interface PenData {
  penId?: string
  type: string
  text?: string
  x: number
  y: number
  width?: number
  height?: number
  background?: string
  color?: string
  fontSize?: number
  borderWidth?: number
  borderColor?: string
}

export interface LineData {
  fromPen: string
  toPen: string
  lineType?: string
  text?: string
  arrow?: string
  color?: string
  lineWidth?: number
}

type PenIdMap = Map<string, string> // logical ID → actual Meta2D pen ID

const penIdMap: PenIdMap = new Map()

const TYPE_MAP: Record<string, string> = {
  rectangle: 'rectangle',
  circle: 'circle',
  triangle: 'triangle',
  diamond: 'diamond',
  pentagon: 'pentagon',
  star: 'star',
  text: 'text',
  image: 'image',
}

const COLOR_DEFAULTS: Record<string, { background: string; color: string }> = {
  rectangle: { background: '#e8f4fd', color: '#1e40af' },
  circle: { background: '#d1fae5', color: '#065f46' },
  triangle: { background: '#fef3c7', color: '#92400e' },
  diamond: { background: '#fce7f3', color: '#9d174d' },
  pentagon: { background: '#ede9fe', color: '#5b21b6' },
  star: { background: '#fff7ed', color: '#9a3412' },
  text: { background: 'transparent', color: '#1f2937' },
  image: { background: '#f3f4f6', color: '#1f2937' },
}

function getMeta2d(): any {
  return (window as any).meta2d
}

/** Push current state to Meta2D undo stack so Agent mutations are Ctrl+Z-able. */
function pushUndoState(meta2d: any): void {
  try {
    if (typeof meta2d.addHistory === 'function') {
      meta2d.addHistory(structuredClone(meta2d.data()))
    }
  } catch (err) {
    console.warn('[canvasBridge] pushUndoState failed:', err)
  }
}

/** Calculate connection anchor point on the edge of a pen, accounting for shape type. */
function getAnchor(pen: any, side: 'top' | 'bottom' | 'center'): { x: number; y: number } {
  const x = pen.x || 0
  const y = pen.y || 0
  const w = pen.width || 120
  const h = pen.height || 60
  const name = (pen.name || pen.type || 'rectangle') as string

  if (side === 'center') {
    return { x: x + w / 2, y: y + h / 2 }
  }

  // Circles: use radius-adjusted points on the circumference
  if (name === 'circle') {
    const cx = x + w / 2
    const cy = y + h / 2
    const r = Math.min(w, h) / 2
    return side === 'bottom' ? { x: cx, y: cy + r } : { x: cx, y: cy - r }
  }

  // Diamonds: the visual tip extends beyond the bounding box
  if (name === 'diamond') {
    if (side === 'bottom') return { x: x + w / 2, y: y + h }
    return { x: x + w / 2, y: y }
  }

  // Triangles: vertices are at mid-top and bottom corners
  if (name === 'triangle') {
    if (side === 'bottom') return { x: x + w / 2, y: y + h }
    return { x: x + w / 2, y: y }
  }

  // Default (rectangle, pentagon, star, text, image, etc.): bounding box edge
  if (side === 'bottom') return { x: x + w / 2, y: y + h }
  return { x: x + w / 2, y: y }
}

/** Validate that referenced pens exist on the canvas. Returns the first missing ID or null. */
function validatePens(meta2d: any, penIds: string[]): string | null {
  for (const id of penIds) {
    const actualId = resolvePenId(id) || id
    if (!meta2d.findOne(actualId)) return id
  }
  return null
}

/**
 * Notify the application that the canvas has been mutated.
 * Ensures localStorage sync + save-state marking + event dispatch.
 * Called by every executeCanvasTool operation.
 */
function notifyCanvasMutation(): void {
  const meta2d = getMeta2d()
  if (!meta2d) return
  try {
    const data = meta2d.data()
    if (data) {
      localStorage.setItem('meta2d', JSON.stringify(data))
    }
  } catch (err) {
    console.warn('[canvasBridge] notifyCanvasMutation localStorage write failed:', err)
  }
  // Dispatch custom event for Index.vue save pipeline
  window.dispatchEvent(new CustomEvent('meta2d:agent-mutation'))
}

export function resolvePenId(logicalId: string): string | undefined {
  return penIdMap.get(logicalId)
}

export function clearPenIdMap(): void {
  penIdMap.clear()
}

export function executeCanvasToolLocalStorage(
  toolName: string,
  args: Record<string, unknown>,
  success: boolean,
  result: unknown,
): boolean {
  // Fallback for pages without meta2d global (e.g., chat page).
  // Modifies localStorage meta2d data so changes appear when canvas page loads.
  if (!success) return false
  try {
    const raw = localStorage.getItem('meta2d')
    let data: any = raw ? JSON.parse(raw) : { pens: [], lines: [] }
    if (!data.pens) data.pens = []
    if (!data.lines) data.lines = []

    const action = (args.action as string) || toolName
    switch (action) {
      case 'add_pen':
      case 'canvas_add_pen': {
        const r = result as Record<string, unknown> | undefined
        const penId = ((r?.pen_id || r?.penId) as string) || `pen_${Date.now()}`
        const penType = ((args.type as string) || 'rectangle').toLowerCase()
        const defaults = COLOR_DEFAULTS[TYPE_MAP[penType]] || COLOR_DEFAULTS.rectangle
        const pen: any = {
          id: penId,
          penId,
          name: TYPE_MAP[penType] || 'rectangle',
          text: (args.text as string) || '',
          x: (args.x as number) || 0,
          y: (args.y as number) || 0,
          width: (args.width as number) || 120,
          height: (args.height as number) || 60,
          background: (args.background as string) || defaults.background,
          color: (args.color as string) || defaults.color,
          fontSize: (args.fontSize as number) || 14,
          lineWidth: (args.borderWidth as number) || 1,
          borderColor: (args.borderColor as string) || '#d1d5db',
        }
        data.pens.push(pen)
        penIdMap.set(penId, penId)
        break
      }
      case 'delete_pen':
      case 'canvas_delete_pen': {
        const ids = (args.pen_ids as string[]) || (args.pen_id ? [args.pen_id as string] : [])
        data.pens = data.pens.filter((p: any) => !ids.includes(p.id) && !ids.includes(p.penId))
        for (const id of ids) penIdMap.delete(id)
        break
      }
      case 'clear':
      case 'canvas_clear':
        if (args.confirm) {
          data.pens = []
          data.lines = []
          penIdMap.clear()
        }
        break
      case 'add_line':
      case 'canvas_add_line': {
        const line: any = {
          id: `line_${Date.now()}`,
          fromPen: args.from_pen,
          toPen: args.to_pen,
          lineType: args.line_type || 'straight',
          text: args.text || '',
          arrow: args.arrow || 'end',
          color: args.color || '#6b7280',
          lineWidth: args.lineWidth || 2,
        }
        data.lines.push(line)
        break
      }
      case 'update_pen':
      case 'canvas_update_pen': {
        const pid = (args.pen_id as string) || ''
        const props = (args.props as Record<string, unknown>) || {}
        if (pid && Object.keys(props).length > 0) {
          const pen = data.pens.find((p: any) => p.id === pid || p.penId === pid)
          if (pen) Object.assign(pen, props)
        }
        break
      }
      case 'add_diagram':
      case 'canvas_add_diagram': {
        const r2 = result as Record<string, unknown> | undefined
        const diag = (r2?.data as Record<string, unknown>)?.diagram as Record<string, unknown> | undefined
        if (!diag) break
        const ns = (diag.nodes || []) as Record<string, unknown>[]
        const es = (diag.edges || []) as Record<string, unknown>[]
        for (const node of ns) {
          const penId = (node.pen_id as string) || `pen_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`
          const penType = ((node.type as string) || 'rectangle').toLowerCase()
          const defaults = COLOR_DEFAULTS[TYPE_MAP[penType]] || COLOR_DEFAULTS.rectangle
          data.pens.push({
            id: penId,
            penId,
            name: TYPE_MAP[penType] || 'rectangle',
            text: (node.text as string) || '',
            x: (node.x as number) || 0,
            y: (node.y as number) || 0,
            width: (node.width as number) || 120,
            height: (node.height as number) || 60,
            background: (node.background as string) || defaults.background,
            color: (node.color as string) || defaults.color,
            fontSize: (node.fontSize as number) || 14,
            lineWidth: (node.borderWidth as number) || 1,
            borderColor: (node.borderColor as string) || '#d1d5db',
          })
        }
        for (const edge of es) {
          data.lines.push({
            id: `line_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`,
            fromPen: edge._from_id || edge.from,
            toPen: edge._to_id || edge.to,
            lineType: edge.line_type || 'straight',
            text: edge.text || '',
            arrow: edge.arrow || 'end',
            color: edge.color || '#6b7280',
            lineWidth: edge.lineWidth || 2,
          })
        }
        break
      }
      case 'undo':
      case 'redo':
      case 'canvas_undo':
      case 'canvas_redo':
        // Not applicable to localStorage mode (no undo stack)
        break
      case 'get_state':
      case 'canvas_get_state':
        break
    }
    localStorage.setItem('meta2d', JSON.stringify(data))
    return true
  } catch (err) {
    console.warn('[canvasBridge] executeCanvasToolLocalStorage failed:', err)
    return false
  }
}

export async function executeCanvasTool(
  toolName: string,
  args: Record<string, unknown>,
  success: boolean,
  result: unknown,
): Promise<boolean> {
  const meta2d = getMeta2d()
  if (!meta2d) {
    return executeCanvasToolLocalStorage(toolName, args, success, result)
  }

  const action = (args.action as string) || toolName
  let ok = false

  switch (action) {
    case 'add_pen':
    case 'canvas_add_pen':
      ok = await _addPen(meta2d, args, success, result)
      break
    case 'add_line':
    case 'canvas_add_line':
      ok = await _addLine(meta2d, args, success, result)
      break
    case 'update_pen':
    case 'canvas_update_pen':
      ok = _updatePen(meta2d, args, success, result)
      break
    case 'delete_pen':
    case 'canvas_delete_pen':
      ok = _deletePen(meta2d, args, success, result)
      break
    case 'clear':
    case 'canvas_clear':
      ok = _clear(meta2d, args, success)
      break
    case 'undo':
    case 'canvas_undo':
      ok = _undo(meta2d, success)
      break
    case 'redo':
    case 'canvas_redo':
      ok = _redo(meta2d, success)
      break
    case 'get_state':
    case 'canvas_get_state':
      return true
    case 'add_diagram':
    case 'canvas_add_diagram':
      ok = await _addDiagram(meta2d, args, success, result)
      break
    case 'layout_auto_arrange':
      ok = _autoArrange(meta2d, args, success)
      break
    case 'layout_align':
      ok = _align(meta2d, args, success)
      break
    default:
      return false
  }

  if (ok) notifyCanvasMutation()
  return ok
}

async function _addPen(
  meta2d: any,
  args: Record<string, unknown>,
  success: boolean,
  result: unknown,
): Promise<boolean> {
  if (!success) return false

  const r = result as Record<string, unknown> | undefined
  const penId = (r?.pen_id || r?.penId) as string | undefined
  const penType = ((args.type as string) || 'rectangle').toLowerCase()
  const name = TYPE_MAP[penType] || 'rectangle'
  const defaults = COLOR_DEFAULTS[name] || COLOR_DEFAULTS.rectangle

  const pen: any = {
    name,
    text: (args.text as string) || '',
    x: (args.x as number) || 0,
    y: (args.y as number) || 0,
    width: (args.width as number) || 120,
    height: (args.height as number) || 60,
    background: (args.background as string) || defaults.background,
    color: (args.color as string) || defaults.color,
    fontSize: (args.fontSize as number) || 14,
    lineWidth: (args.borderWidth as number) || 1,
    borderColor: (args.borderColor as string) || '#d1d5db',
  }

  if (name === 'circle') {
    pen.width = pen.height = Math.min(pen.width, pen.height) || 80
  }

  pushUndoState(meta2d)
  try {
    const p = await meta2d.addPen(pen)
    const realId = (p as any)?.id || (p as any)?.penId
    if (penId && realId) {
      penIdMap.set(penId, realId)
    }
    return true
  } catch (err) {
    console.warn('[canvasBridge] _addPen failed:', err)
    return false
  }
}

async function _addLine(
  meta2d: any,
  args: Record<string, unknown>,
  success: boolean,
  _result: unknown,
): Promise<boolean> {
  if (!success) return false

  const fromLogical = args.from_pen as string
  const toLogical = args.to_pen as string
  const fromId = resolvePenId(fromLogical) || fromLogical
  const toId = resolvePenId(toLogical) || toLogical

  const fromPen = meta2d.findOne(fromId)
  const toPen = meta2d.findOne(toId)
  if (!fromPen || !toPen) {
    console.warn(`[canvasBridge] add_line: pen not found — from="${fromId}" to="${toId}"`)
    return false
  }

  const lineType = (args.line_type as string) || 'straight'
  const arrow = (args.arrow as string) || 'end'

  // Use shape-aware anchor points (fix: was hardcoded rectangle bottom→top)
  const fromAnchor = getAnchor(fromPen, 'bottom')
  const toAnchor = getAnchor(toPen, 'top')

  const line: any = {
    name: 'line',
    type: 1,
    lineName: lineType === 'mind' ? 'mind' : lineType === 'curve' ? 'curve' : 'line',
    anchors: [fromAnchor, toAnchor],
    source: { id: fromPen.id, connectTo: toPen.id },
    text: (args.text as string) || '',
    lineWidth: (args.lineWidth as number) || 2,
    color: (args.color as string) || '#6b7280',
    fontSize: 13,
  }

  if (arrow === 'start' || arrow === 'both') line.fromArrow = 'triangleSolid'
  if (arrow === 'end' || arrow === 'both') line.toArrow = 'triangleSolid'

  pushUndoState(meta2d)
  await meta2d.addPen(line)

  return true
}

function _updatePen(meta2d: any, args: Record<string, unknown>, success: boolean, _result: unknown): boolean {
  if (!success) return false

  const logicalId = args.pen_id as string
  const actualId = resolvePenId(logicalId) || logicalId
  const props = (args.props as Record<string, unknown>) || {}
  if (!actualId || Object.keys(props).length === 0) return false

  const pen = meta2d.findOne(actualId)
  if (!pen) {
    console.warn(`[canvasBridge] update_pen: pen not found — id="${actualId}"`)
    return false
  }

  pushUndoState(meta2d)
  meta2d.setValue({ id: actualId, ...props }, { render: false })
  meta2d.render()
  return true
}

function _deletePen(meta2d: any, args: Record<string, unknown>, success: boolean): boolean {
  if (!success) return false

  const penIds = (args.pen_ids as string[]) || (args.pen_id ? [args.pen_id as string] : [])
  const toDelete: string[] = []
  for (const id of penIds) {
    const actual = resolvePenId(id) || id
    toDelete.push(actual)
  }
  if (toDelete.length === 0) return false

  const pens = toDelete.map(id => meta2d.findOne(id)).filter(Boolean)
  if (pens.length === 0) {
    console.warn(`[canvasBridge] delete_pen: no pens found for ids=${toDelete.join(',')}`)
    return false
  }

  pushUndoState(meta2d)
  meta2d.delete(pens)
  meta2d.render()
  for (const id of penIds) penIdMap.delete(id)
  return true
}

function _clear(meta2d: any, args: Record<string, unknown>, success: boolean): boolean {
  if (!success || !args.confirm) return false
  const data = meta2d.data()
  if (data?.pens?.length > 0) {
    pushUndoState(meta2d)
    meta2d.delete(data.pens)
    meta2d.render()
  }
  penIdMap.clear()
  return true
}

async function _addDiagram(
  meta2d: any,
  args: Record<string, unknown>,
  success: boolean,
  result: unknown,
): Promise<boolean> {
  if (!success) return false

  const r = result as Record<string, unknown> | undefined
  const diagram = (r?.data as Record<string, unknown>)?.diagram as Record<string, unknown> | undefined
  if (!diagram) return false

  const nodes = (diagram.nodes || []) as Record<string, unknown>[]
  const edges = (diagram.edges || []) as Record<string, unknown>[]
  const logicalToActual = new Map<string, string>()

  pushUndoState(meta2d)

  // Phase 1: Create all pens
  for (const node of nodes) {
    const penType = ((node.type as string) || 'rectangle').toLowerCase()
    const name = TYPE_MAP[penType] || 'rectangle'
    const defaults = COLOR_DEFAULTS[name] || COLOR_DEFAULTS.rectangle
    const pen: any = {
      name,
      text: (node.text as string) || '',
      x: (node.x as number) || 0,
      y: (node.y as number) || 0,
      width: (node.width as number) || 120,
      height: (node.height as number) || 60,
      background: (node.background as string) || defaults.background,
      color: (node.color as string) || defaults.color,
      fontSize: (node.fontSize as number) || 14,
      lineWidth: (node.borderWidth as number) || 1,
      borderColor: (node.borderColor as string) || '#d1d5db',
    }
    if (name === 'circle') {
      pen.width = pen.height = Math.min(pen.width, pen.height) || 80
    }
    const actualPen = await meta2d.addPen(pen)
    if (actualPen) {
      const logicalId = (node.pen_id as string) || (node.id as string) || ''
      const actualId = actualPen.id || actualPen.penId || ''
      if (logicalId) logicalToActual.set(logicalId, actualId)
      if (logicalId) penIdMap.set(logicalId, actualId)
    }
  }

  // Phase 2: Create all lines (shape-aware anchors)
  for (const edge of edges) {
    const fromLogical = (edge._from_id as string) || (edge.from as string) || ''
    const toLogical = (edge._to_id as string) || (edge.to as string) || ''
    const fromId = logicalToActual.get(fromLogical) || fromLogical
    const toId = logicalToActual.get(toLogical) || toLogical

    const fromPen = meta2d.findOne(fromId)
    const toPen = meta2d.findOne(toId)
    if (!fromPen || !toPen) continue

    const lineType = (edge.line_type as string) || 'straight'
    const arrow = (edge.arrow as string) || 'end'
    const fromAnchor = getAnchor(fromPen, 'bottom')
    const toAnchor = getAnchor(toPen, 'top')

    const line: any = {
      name: 'line',
      type: 1,
      lineName: lineType === 'mind' ? 'mind' : lineType === 'curve' ? 'curve' : 'line',
      anchors: [fromAnchor, toAnchor],
      text: (edge.text as string) || '',
      lineWidth: (edge.lineWidth as number) || 2,
      color: (edge.color as string) || '#6b7280',
      fontSize: 13,
    }
    if (arrow === 'start' || arrow === 'both') line.fromArrow = 'triangleSolid'
    if (arrow === 'end' || arrow === 'both') line.toArrow = 'triangleSolid'

    await meta2d.addPen(line)
  }

  meta2d.render()
  return true
}

function _undo(meta2d: any, success: boolean): boolean {
  if (!success) return false
  meta2d.undo()
  meta2d.render()
  return true
}

function _redo(meta2d: any, success: boolean): boolean {
  if (!success) return false
  meta2d.redo()
  meta2d.render()
  return true
}

function _autoArrange(meta2d: any, args: Record<string, unknown>, success: boolean): boolean {
  if (!success) return false
  const direction = (args.direction as string) || 'vertical'
  const spacing = (args.spacing as number) || 40

  const data = meta2d.data()
  const pens = (data?.pens || []) as any[]
  if (pens.length < 2) return true

  pushUndoState(meta2d)

  // Sort pens top-to-bottom, then arrange
  const sorted = [...pens].sort((a, b) => (a.y || 0) - (b.y || 0))
  let pos = sorted[0]?.y || 0
  for (const pen of sorted) {
    if (direction === 'vertical') {
      meta2d.setValue({ id: pen.id, y: pos }, { render: false })
      pos += (pen.height || 60) + spacing
    } else if (direction === 'horizontal') {
      meta2d.setValue({ id: pen.id, x: pos }, { render: false })
      pos += (pen.width || 120) + spacing
    }
  }
  meta2d.render()
  return true
}

function _align(meta2d: any, args: Record<string, unknown>, success: boolean): boolean {
  if (!success) return false
  const align = (args.align as string) || 'center'
  const data = meta2d.data()
  const pens = (data?.pens || []) as any[]
  if (pens.length < 2) return true

  pushUndoState(meta2d)

  const refPen = pens[0]
  const refX = refPen.x || 0
  const refY = refPen.y || 0
  const refW = refPen.width || 120
  const refH = refPen.height || 60

  for (let i = 1; i < pens.length; i++) {
    const p = pens[i]
    const pw = p.width || 120
    const ph = p.height || 60
    let x = p.x,
      y = p.y
    switch (align) {
      case 'left':
        x = refX
        break
      case 'center':
        x = refX + refW / 2 - pw / 2
        break
      case 'right':
        x = refX + refW - pw
        break
      case 'top':
        y = refY
        break
      case 'middle':
        y = refY + refH / 2 - ph / 2
        break
      case 'bottom':
        y = refY + refH - ph
        break
    }
    meta2d.setValue({ id: p.id, x, y }, { render: false })
  }
  meta2d.render()
  return true
}
