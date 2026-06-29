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
  // 填充/边框
  background?: string
  color?: string
  borderColor?: string
  borderWidth?: number
  borderRadius?: number
  lineDash?: number[]
  globalAlpha?: number
  // 阴影
  shadowColor?: string
  shadowBlur?: number
  shadowOffsetX?: number
  shadowOffsetY?: number
  // 渐变
  gradientColors?: string
  lineGradientColors?: string
  // 文字
  fontSize?: number
  fontFamily?: string
  fontWeight?: string
  fontStyle?: string
  textAlign?: string
  textBaseline?: string
  // 图标
  icon?: string
  iconFamily?: string
  iconSize?: number
  iconColor?: string
  // 图片
  image?: string
  imageRatio?: boolean
  // 内边距
  paddingTop?: number
  paddingBottom?: number
  paddingLeft?: number
  paddingRight?: number
  // 状态
  visible?: boolean
  locked?: number
  tags?: string[]
}

export interface LineData {
  fromPen: string
  toPen: string
  lineType?: string
  text?: string
  arrow?: string
  color?: string
  lineWidth?: number
  fromArrow?: string
  toArrow?: string
}

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
  } catch { /* ignore */ }
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

/**
 * Notify the application that the canvas has been mutated.
 * Ensures localStorage sync + save-state marking + event dispatch.
 * Debounced to batch rapid successive mutations (e.g. add_diagram creates many pens).
 */
let _mutationTimer: ReturnType<typeof setTimeout> | null = null

function notifyCanvasMutation(): void {
  if (_mutationTimer) clearTimeout(_mutationTimer)
  _mutationTimer = setTimeout(() => {
    const meta2d = getMeta2d()
    if (!meta2d) return
    try {
      const data = meta2d.data()
      if (data) {
        localStorage.setItem('meta2d', JSON.stringify(data))
      }
    } catch { /* ignore */ }
    window.dispatchEvent(new CustomEvent('meta2d:agent-mutation'))
    _mutationTimer = null
  }, 100)
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
        const penId = (r?.pen_id || r?.penId) as string || `pen_${Date.now()}`
        const pen = _buildPen(args, penId)
        data.pens.push(pen)
        break
      }
      case 'delete_pen':
      case 'canvas_delete_pen': {
        const ids = _resolveIds(args)
        data.pens = data.pens.filter((p: any) => !ids.includes(p.id) && !ids.includes(p.penId))
        break
      }
      case 'clear':
      case 'canvas_clear':
        if (args.confirm) { data.pens = []; data.lines = [] }
        break
      case 'add_line':
      case 'canvas_add_line': {
        const fromId = args.from_pen as string
        const toId = args.to_pen as string
        const arrow = (args.arrow as string) || 'end'
        const line: any = {
          id: `line_${Date.now()}`,
          fromPen: fromId,
          toPen: toId,
          lineType: args.line_type || 'straight',
          text: args.text || '',
          color: args.color || '#6b7280',
          lineWidth: args.lineWidth || 2,
        }
        if (arrow === 'start' || arrow === 'both') line.fromArrow = 'triangleSolid'
        if (arrow === 'end' || arrow === 'both') line.toArrow = 'triangleSolid'
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
          data.pens.push(_buildPen(node as Record<string, unknown>, penId))
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
      case 'lock':
      case 'unlock': {
        const lockedVal = action === 'lock' ? 2 : 0
        for (const id of _resolveIds(args)) {
          const pen = data.pens.find((p: any) => p.id === id || p.penId === id)
          if (pen) pen.locked = lockedVal
        }
        break
      }
      case 'toggle_visibility': {
        const vis = args.visible as boolean
        for (const id of _resolveIds(args)) {
          const pen = data.pens.find((p: any) => p.id === id || p.penId === id)
          if (pen) pen.visible = vis
        }
        break
      }
      case 'duplicate': {
        const ids = _resolveIds(args)
        const ox = (args.offset_x as number) || 30
        const oy = (args.offset_y as number) || 30
        const r3 = result as Record<string, unknown> | undefined
        const newIds = (r3?.data as any)?.new_ids || []
        for (let i = 0; i < ids.length; i++) {
          const src = data.pens.find((p: any) => p.id === ids[i] || p.penId === ids[i])
          if (src) {
            const clone = { ...src, id: newIds[i] || `pen_${Date.now()}_${i}`, penId: newIds[i], x: (src.x || 0) + ox, y: (src.y || 0) + oy }
            data.pens.push(clone)
          }
        }
        break
      }
      case 'move_pen': {
        for (const m of (args.moves as Array<{pen_id: string; x: number; y: number}>) || []) {
          const pen = data.pens.find((p: any) => p.id === m.pen_id || p.penId === m.pen_id)
          if (pen) { pen.x = m.x; pen.y = m.y }
        }
        break
      }
      case 'group':
      case 'ungroup':
        // localStorage mode doesn't support combine/uncombine — pens just persist
        break
      case 'canvas_props': {
        for (const key of ['background', 'bkImage', 'gridColor', 'color', 'penBackground', 'ruleColor']) {
          if (args[key] !== undefined) data[key] = args[key]
        }
        for (const key of ['grid', 'rule']) {
          if (args[key] !== undefined) data[key] = args[key] ? '1' : '0'
        }
        if (args.gridSize !== undefined) data.gridSize = String(args.gridSize)
        break
      }
      case 'fit_view':
        // Not applicable to localStorage mode
        break
      case 'undo':
      case 'redo':
      case 'canvas_undo':
      case 'canvas_redo':
        // Not applicable to localStorage mode (no undo stack)
        break
      case 'get_state':
      case 'canvas_get_state':
      case 'canvas_check_empty':
        break
    }
    localStorage.setItem('meta2d', JSON.stringify(data))
    return true
  } catch {
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

  try {
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
        ok = _deletePen(meta2d, args, success)
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
      case 'canvas_check_empty':
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
      // ── New actions ──
      case 'lock':
      case 'unlock':
        ok = _setLockState(meta2d, args, success, action === 'lock' ? 2 : 0)
        break
      case 'toggle_visibility':
        ok = _toggleVisibility(meta2d, args, success)
        break
      case 'duplicate':
        ok = await _duplicatePens(meta2d, args, success, result)
        break
      case 'move_pen':
        ok = _movePen(meta2d, args, success)
        break
      case 'group':
        ok = _groupPens(meta2d, args, success)
        break
      case 'ungroup':
        ok = _ungroupPen(meta2d, args, success)
        break
      case 'canvas_props':
        ok = _setCanvasProps(meta2d, args, success)
        break
      case 'fit_view':
        ok = _fitView(meta2d, args, success)
        break
      default:
        return false
    }
  } catch (e) {
    console.warn(`[canvasBridge] ${action} failed:`, e)
    return false
  }

  if (ok) notifyCanvasMutation()
  return ok
}

/** Build a Meta2D pen object from tool args, applying defaults. Only sets non-undefined values. */
function _buildPen(args: Record<string, unknown>, penId: string): any {
  const penType = ((args.type as string) || 'rectangle').toLowerCase()
  const name = TYPE_MAP[penType] || 'rectangle'
  const defaults = COLOR_DEFAULTS[name] || COLOR_DEFAULTS.rectangle

  const pen: any = {
    id: penId,
    name,
    text: args.text || '',
    x: (args.x as number) || 0,
    y: (args.y as number) || 0,
    width: (args.width as number) || 120,
    height: (args.height as number) || 60,
    background: args.background || defaults.background,
    color: args.color || defaults.color,
    borderColor: args.borderColor || '#d1d5db',
    fontSize: args.fontSize ?? 14,
  }

  // Optional properties — only set when explicitly provided
  const optionalProps: [string, string][] = [
    ['borderWidth', 'borderWidth'], ['borderRadius', 'borderRadius'],
    ['lineDash', 'lineDash'], ['globalAlpha', 'globalAlpha'],
    ['shadowColor', 'shadowColor'], ['shadowBlur', 'shadowBlur'],
    ['shadowOffsetX', 'shadowOffsetX'], ['shadowOffsetY', 'shadowOffsetY'],
    ['gradientColors', 'gradientColors'], ['lineGradientColors', 'lineGradientColors'],
    ['fontFamily', 'fontFamily'], ['fontWeight', 'fontWeight'],
    ['fontStyle', 'fontStyle'], ['textAlign', 'textAlign'], ['textBaseline', 'textBaseline'],
    ['icon', 'icon'], ['iconFamily', 'iconFamily'], ['iconSize', 'iconSize'], ['iconColor', 'iconColor'],
    ['image', 'image'], ['imageRatio', 'imageRatio'],
    ['paddingTop', 'paddingTop'], ['paddingBottom', 'paddingBottom'],
    ['paddingLeft', 'paddingLeft'], ['paddingRight', 'paddingRight'],
    ['visible', 'visible'], ['locked', 'locked'], ['tags', 'tags'],
  ]
  for (const [argKey, penKey] of optionalProps) {
    if (args[argKey] !== undefined) pen[penKey] = args[argKey]
  }

  if (name === 'circle') {
    pen.width = pen.height = Math.min(pen.width, pen.height) || 80
  }

  return pen
}

/** Build a Meta2D line pen connecting two existing pens. */
function _buildLine(fromPen: any, toPen: any, opts: {
  lineType?: string; arrow?: string; text?: string; lineWidth?: number; color?: string;
}): any {
  const lineType = opts.lineType || 'straight'
  const arrow = opts.arrow || 'end'
  const fromAnchor = getAnchor(fromPen, 'bottom')
  const toAnchor = getAnchor(toPen, 'top')

  const line: any = {
    name: 'line',
    type: 1,
    lineName: lineType === 'mind' ? 'mind' : lineType === 'curve' ? 'curve' : 'line',
    anchors: [fromAnchor, toAnchor],
    source: { id: fromPen.id, connectTo: toPen.id },
    text: opts.text || '',
    lineWidth: opts.lineWidth || 2,
    color: opts.color || '#6b7280',
    fontSize: 13,
  }
  if (arrow === 'start' || arrow === 'both') line.fromArrow = 'triangleSolid'
  if (arrow === 'end' || arrow === 'both') line.toArrow = 'triangleSolid'
  return line
}

/** Resolve pen_ids from args — supports single pen_id or list. */
function _resolveIds(args: Record<string, unknown>): string[] {
  return (args.pen_ids as string[]) || (args.pen_id ? [args.pen_id as string] : [])
}

async function _addPen(meta2d: any, args: Record<string, unknown>, success: boolean, result: unknown): Promise<boolean> {
  if (!success) return false

  const r = result as Record<string, unknown> | undefined
  const penId = (r?.pen_id || r?.penId) as string || `pen_${Date.now()}`
  const pen = _buildPen(args, penId)

  pushUndoState(meta2d)
  await meta2d.addPen(pen)

  return true
}

async function _addLine(meta2d: any, args: Record<string, unknown>, success: boolean, _result: unknown): Promise<boolean> {
  if (!success) return false

  const fromPen = meta2d.findOne(args.from_pen as string)
  const toPen = meta2d.findOne(args.to_pen as string)
  if (!fromPen || !toPen) {
    console.warn(`[canvasBridge] add_line: pen not found — from="${args.from_pen}" to="${args.to_pen}"`)
    return false
  }

  const line = _buildLine(fromPen, toPen, {
    lineType: args.line_type as string,
    arrow: args.arrow as string,
    text: args.text as string,
    lineWidth: args.lineWidth as number,
    color: args.color as string,
  })

  pushUndoState(meta2d)
  await meta2d.addPen(line)
  return true
}

function _updatePen(meta2d: any, args: Record<string, unknown>, success: boolean, _result: unknown): boolean {
  if (!success) return false

  // Support single pen (pen_id + props) or batch (updates: [{pen_id, props}])
  const updates: Array<{ pen_id: string; props: Record<string, unknown> }> =
    (args.updates as any) || [{ pen_id: args.pen_id as string, props: (args.props as Record<string, unknown>) || {} }]

  if (updates.length === 0) return false

  pushUndoState(meta2d)
  for (const u of updates) {
    if (!u.pen_id) continue
    meta2d.setValue({ id: u.pen_id, ...u.props }, { render: false })
  }
  meta2d.render()
  return true
}

function _deletePen(meta2d: any, args: Record<string, unknown>, success: boolean): boolean {
  if (!success) return false

  const penIds = (args.pen_ids as string[]) || (args.pen_id ? [args.pen_id as string] : [])
  if (penIds.length === 0) return false

  const pens = penIds.map((id) => meta2d.findOne(id)).filter(Boolean)
  if (pens.length === 0) {
    console.warn(`[canvasBridge] delete_pen: no pens found for ids=${penIds.join(',')}`)
    return false
  }

  pushUndoState(meta2d)
  meta2d.delete(pens)
  meta2d.render()
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
  return true
}

async function _addDiagram(meta2d: any, _args: Record<string, unknown>, success: boolean, result: unknown): Promise<boolean> {
  if (!success) return false

  const r = result as Record<string, unknown> | undefined
  const diagram = (r?.data as Record<string, unknown>)?.diagram as Record<string, unknown> | undefined
  if (!diagram) return false

  const nodes = (diagram.nodes || []) as Record<string, unknown>[]
  const edges = (diagram.edges || []) as Record<string, unknown>[]

  pushUndoState(meta2d)

  // Phase 1: Create all pens using backend-generated UUIDs as pen IDs
  for (const node of nodes) {
    const penId = (node.pen_id as string) || `pen_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`
    // Pass node props as args to _buildPen
    const pen = _buildPen(node as Record<string, unknown>, penId)
    await meta2d.addPen(pen)
  }

  // Phase 2: Create all lines using the pen_id assigned by backend
  for (const edge of edges) {
    const fromPen = meta2d.findOne((edge._from_id || edge.from) as string || '')
    const toPen = meta2d.findOne((edge._to_id || edge.to) as string || '')
    if (!fromPen || !toPen) continue

    const line = _buildLine(fromPen, toPen, {
      lineType: edge.line_type as string,
      arrow: edge.arrow as string,
      text: edge.text as string,
      lineWidth: edge.lineWidth as number,
      color: edge.color as string,
    })
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
    let x = p.x, y = p.y
    switch (align) {
      case 'left': x = refX; break
      case 'center': x = refX + refW / 2 - pw / 2; break
      case 'right': x = refX + refW - pw; break
      case 'top': y = refY; break
      case 'middle': y = refY + refH / 2 - ph / 2; break
      case 'bottom': y = refY + refH - ph; break
    }
    meta2d.setValue({ id: p.id, x, y }, { render: false })
  }
  meta2d.render()
  return true
}

// ─── New action handlers ────────────────────────────────────────────────

/** Batch setValue on multiple pens with a single render + undo entry. */
function _batchSetValue(meta2d: any, updates: Array<{ id: string;[key: string]: unknown }>): void {
  pushUndoState(meta2d)
  for (const u of updates) {
    meta2d.setValue(u, { render: false })
  }
  meta2d.render()
}

function _setLockState(meta2d: any, args: Record<string, unknown>, success: boolean, lockedVal: number): boolean {
  if (!success) return false
  const ids = _resolveIds(args)
  if (ids.length === 0) return false
  _batchSetValue(meta2d, ids.map(id => ({ id, locked: lockedVal })))
  return true
}

function _toggleVisibility(meta2d: any, args: Record<string, unknown>, success: boolean): boolean {
  if (!success) return false
  const ids = _resolveIds(args)
  if (ids.length === 0) return false
  _batchSetValue(meta2d, ids.map(id => ({ id, visible: args.visible as boolean })))
  return true
}

async function _duplicatePens(meta2d: any, args: Record<string, unknown>, success: boolean, _result: unknown): Promise<boolean> {
  if (!success) return false
  const ids = _resolveIds(args)
  if (ids.length === 0) return false

  const ox = (args.offset_x as number) || 30
  const oy = (args.offset_y as number) || 30
  const pens = ids.map((id) => meta2d.findOne(id)).filter(Boolean)
  if (pens.length === 0) return false

  pushUndoState(meta2d)
  meta2d.copy(pens)
  meta2d.paste()
  // Offset the newly pasted pens (they become the active selection)
  _batchSetValue(meta2d, (meta2d.active || []).map((id: string) => {
    const p = meta2d.findOne(id)
    return { id, x: (p?.x || 0) + ox, y: (p?.y || 0) + oy }
  }))
  return true
}

function _movePen(meta2d: any, args: Record<string, unknown>, success: boolean): boolean {
  if (!success) return false
  const moves = (args.moves as Array<{ pen_id: string; x: number; y: number }>) || []
  if (moves.length === 0) return false
  _batchSetValue(meta2d, moves.filter(m => m.pen_id).map(m => ({ id: m.pen_id, x: m.x, y: m.y })))
  return true
}

function _groupPens(meta2d: any, args: Record<string, unknown>, success: boolean): boolean {
  if (!success) return false
  const pens = _resolveIds(args).map((id) => meta2d.findOne(id)).filter(Boolean)
  if (pens.length < 2) return false
  pushUndoState(meta2d)
  meta2d.combine(pens)
  meta2d.render()
  return true
}

function _ungroupPen(meta2d: any, args: Record<string, unknown>, success: boolean): boolean {
  if (!success) return false
  const pen = meta2d.findOne(args.pen_id as string)
  if (!pen) return false
  pushUndoState(meta2d)
  meta2d.uncombine(pen)
  meta2d.render()
  return true
}

function _setCanvasProps(meta2d: any, args: Record<string, unknown>, success: boolean): boolean {
  if (!success) return false
  // Bool props need conversion to Meta2D string format
  const BOOL_PROPS = ['grid', 'rule']
  const props: Record<string, unknown> = {}
  for (const key of ['background', 'bkImage', 'gridColor', 'color', 'penBackground']) {
    if (args[key] !== undefined) props[key] = args[key]
  }
  for (const key of BOOL_PROPS) {
    if (args[key] !== undefined) props[key] = args[key] ? '1' : '0'
  }
  if (args.gridSize !== undefined) props.gridSize = String(args.gridSize)
  if (args.ruleColor !== undefined) props.ruleColor = args.ruleColor

  if (Object.keys(props).length === 0) return true
  meta2d.setValue(props, { render: false })
  meta2d.render()
  return true
}

function _fitView(meta2d: any, args: Record<string, unknown>, success: boolean): boolean {
  if (!success) return false
  if (args.fit !== false) {
    meta2d.fitView(true, (args.padding as number) ?? 24)
  } else {
    meta2d.fitView(false)
  }
  return true
}

/** Build a human-readable summary of canvas mutations for Agent tool card feedback. */
export function getCanvasMutationSummary(
  tool: string,
  args: Record<string, unknown>,
  success: boolean,
  result: unknown,
): string | null {
  if (!success) return null
  const action = (args.action as string) || tool
  const r = result as Record<string, unknown> | undefined

  switch (action) {
    case 'add_pen':
    case 'canvas_add_pen': {
      const penType = (args.type as string) || 'rectangle'
      const text = (args.text as string) || ''
      const label = text ? `"${text.slice(0, 40)}"` : penType
      return `已添加 ${label}`
    }
    case 'add_line':
    case 'canvas_add_line': {
      const text = (args.text as string) || ''
      return text ? `已添加连线 "${text.slice(0, 30)}"` : '已添加连线'
    }
    case 'add_diagram':
    case 'canvas_add_diagram': {
      const diag = (r?.data as Record<string, unknown>)?.diagram as Record<string, unknown> | undefined
      if (!diag) return '已添加图表'
      const nodes = (diag.nodes || []) as any[]
      const edges = (diag.edges || []) as any[]
      return `已添加图表: ${nodes.length} 个节点, ${edges.length} 条连线`
    }
    case 'update_pen':
    case 'canvas_update_pen': {
      const pid = (args.pen_id as string) || ''
      const props = args.props as Record<string, unknown> | undefined
      const keys = props ? Object.keys(props).join(', ') : ''
      return `已更新节点 ${pid} (${keys})`
    }
    case 'delete_pen':
    case 'canvas_delete_pen': {
      const ids = _resolveIds(args)
      return `已删除 ${ids.length} 个节点`
    }
    case 'clear':
    case 'canvas_clear':
      return '已清空画布'
    case 'undo':
    case 'canvas_undo':
      return '已撤销'
    case 'redo':
    case 'canvas_redo':
      return '已重做'
    case 'lock': {
      const ids = _resolveIds(args)
      return `已锁定 ${ids.length} 个节点`
    }
    case 'unlock': {
      const ids = _resolveIds(args)
      return `已解锁 ${ids.length} 个节点`
    }
    case 'toggle_visibility': {
      const ids = _resolveIds(args)
      const vis = args.visible ? '显示' : '隐藏'
      return `已${vis} ${ids.length} 个节点`
    }
    case 'duplicate': {
      const ids = _resolveIds(args)
      return `已复制 ${ids.length} 个节点`
    }
    case 'move_pen': {
      const moves = (args.moves as any[]) || []
      return `已移动 ${moves.length} 个节点`
    }
    case 'group': {
      const ids = _resolveIds(args)
      return `已组合 ${ids.length} 个节点`
    }
    case 'ungroup':
      return '已取消组合'
    case 'canvas_props': {
      const keys = Object.keys(args).filter(k => k !== 'action' && args[k] !== undefined)
      return `已更新画布属性 (${keys.join(', ')})`
    }
    case 'fit_view':
      return '已自适应视口'
    case 'layout_auto_arrange': {
      const dir = (args.direction as string) || 'vertical'
      const label = dir === 'vertical' ? '垂直' : dir === 'horizontal' ? '水平' : '网格'
      return `已${label}排列节点`
    }
    case 'layout_align': {
      const align = (args.align as string) || 'center'
      const labels: Record<string, string> = { left: '左', center: '中', right: '右', top: '上', middle: '中', bottom: '下' }
      return `已${labels[align] || align}对齐节点`
    }
    default:
      return null
  }
}
