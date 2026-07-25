/**
 * layoutEngine — Canvas auto-arrangement algorithms.
 *
 * Provides 4 layout strategies:
 *  - grid:     simple row/column arrangement (existing behavior)
 *  - tree:     BFS from root, children arranged below parent
 *  - force:    iterative repulsion/attraction (force-directed)
 *  - layered:  Sugiyama-style topological layering for DAGs/flowcharts
 */

export interface Pen {
  id: string
  x: number
  y: number
  width: number
  height: number
}

export interface Line {
  from: string
  to: string
}

export interface LayoutOpts {
  direction?: 'horizontal' | 'vertical'
  spacing?: number
  rootPenId?: string
  width?: number
}

export interface LayoutResult {
  positions: { id: string; x: number; y: number }[]
}

/** Grid layout -- simple row/column arrangement (existing behavior). */
export function gridLayout(pens: Pen[], _lines: Line[], opts: LayoutOpts): LayoutResult {
  const direction = opts.direction || 'vertical'
  const spacing = opts.spacing || 40
  const positions: LayoutResult['positions'] = []
  let cx = 100
  let cy = 100
  for (const p of pens) {
    positions.push({ id: p.id, x: cx, y: cy })
    if (direction === 'vertical') {
      cy += p.height + spacing
    } else {
      cx += p.width + spacing
    }
  }
  return { positions }
}

/** Tree layout -- BFS from root, children arranged below parent. */
export function treeLayout(pens: Pen[], lines: Line[], opts: LayoutOpts): LayoutResult {
  const spacing = opts.spacing || 60
  const rootId = opts.rootPenId || pens[0]?.id
  if (!rootId) return { positions: [] }

  // Build adjacency (parent -> children) from lines
  const children = new Map<string, string[]>()
  for (const l of lines) {
    if (!children.has(l.from)) children.set(l.from, [])
    children.get(l.from)!.push(l.to)
  }

  // BFS to assign depth
  const penMap = new Map(pens.map(p => [p.id, p]))
  const visited = new Set<string>()
  const depthNodes = new Map<number, string[]>()
  const queue: { id: string; depth: number }[] = [{ id: rootId, depth: 0 }]

  while (queue.length > 0) {
    const { id, depth } = queue.shift()!
    if (visited.has(id)) continue
    visited.add(id)
    if (!depthNodes.has(depth)) depthNodes.set(depth, [])
    depthNodes.get(depth)!.push(id)
    for (const childId of (children.get(id) || [])) {
      if (!visited.has(childId)) queue.push({ id: childId, depth: depth + 1 })
    }
  }

  // Position by depth
  const maxDepth = Math.max(...depthNodes.keys(), 0)
  const positions: LayoutResult['positions'] = []
  for (let d = 0; d <= maxDepth; d++) {
    const nodes = depthNodes.get(d) || []
    const totalWidth = nodes.reduce((sum, id) => sum + (penMap.get(id)?.width || 100) + spacing, -spacing)
    let cx = (opts.width || 1200) / 2 - totalWidth / 2
    const cy = 100 + d * 160
    for (const id of nodes) {
      positions.push({ id, x: cx, y: cy })
      cx += (penMap.get(id)?.width || 100) + spacing
    }
  }
  return { positions }
}

/** Force-directed layout -- simple iterative repulsion/attraction. */
export function forceLayout(pens: Pen[], lines: Line[], opts: LayoutOpts): LayoutResult {
  const ITERATIONS = 100
  const positions = new Map<string, { x: number; y: number; vx: number; vy: number }>()
  const cx = (opts.width || 1200) / 2
  const cy = 400
  const radius = Math.min(400, pens.length * 20)

  // Initialize in a circle
  for (let i = 0; i < pens.length; i++) {
    const angle = (2 * Math.PI * i) / pens.length
    positions.set(pens[i].id, {
      x: cx + radius * Math.cos(angle),
      y: cy + radius * Math.sin(angle),
      vx: 0,
      vy: 0,
    })
  }

  const ids = [...positions.keys()]
  const REPULSION = 5000
  const ATTRACTION = 0.01
  const DAMPING = 0.9

  for (let iter = 0; iter < ITERATIONS; iter++) {
    // Repulsion between all pairs
    for (let i = 0; i < ids.length; i++) {
      for (let j = i + 1; j < ids.length; j++) {
        const a = positions.get(ids[i])!
        const b = positions.get(ids[j])!
        let dx = a.x - b.x
        let dy = a.y - b.y
        const dist = Math.max(Math.sqrt(dx * dx + dy * dy), 1)
        const force = REPULSION / (dist * dist)
        a.vx += (dx / dist) * force
        a.vy += (dy / dist) * force
        b.vx -= (dx / dist) * force
        b.vy -= (dy / dist) * force
      }
    }

    // Attraction along edges
    for (const l of lines) {
      const a = positions.get(l.from)
      const b = positions.get(l.to)
      if (!a || !b) continue
      const dx = b.x - a.x
      const dy = b.y - a.y
      const dist = Math.sqrt(dx * dx + dy * dy)
      const force = dist * ATTRACTION
      a.vx += (dx / dist) * force
      a.vy += (dy / dist) * force
      b.vx -= (dx / dist) * force
      b.vy -= (dy / dist) * force
    }

    // Apply velocities with damping
    for (const p of positions.values()) {
      p.vx *= DAMPING
      p.vy *= DAMPING
      p.x += p.vx
      p.y += p.vy
    }
  }

  return {
    positions: [...positions.entries()].map(([id, p]) => ({
      id,
      x: Math.round(p.x),
      y: Math.round(p.y),
    })),
  }
}

/** Layered (Sugiyama-style) layout -- for DAGs/flowcharts. */
export function layeredLayout(pens: Pen[], lines: Line[], opts: LayoutOpts): LayoutResult {
  const spacing = opts.spacing || 80
  const penMap = new Map(pens.map(p => [p.id, p]))

  // Topological layering
  const inDegree = new Map<string, number>()
  const outEdges = new Map<string, string[]>()
  for (const p of pens) {
    inDegree.set(p.id, 0)
    outEdges.set(p.id, [])
  }
  for (const l of lines) {
    inDegree.set(l.to, (inDegree.get(l.to) || 0) + 1)
    if (!outEdges.has(l.from)) outEdges.set(l.from, [])
    outEdges.get(l.from)!.push(l.to)
    if (!inDegree.has(l.from)) inDegree.set(l.from, 0)
  }

  const layers: string[][] = []
  const layerMap = new Map<string, number>()
  const queue: string[] = [...inDegree.entries()]
    .filter(([, d]) => d === 0)
    .map(([id]) => id)

  for (const id of queue) {
    const maxParentLayer = lines
      .filter(l => l.to === id)
      .reduce((max, l) => Math.max(max, layerMap.get(l.from) ?? -1), -1)
    const layer = maxParentLayer + 1
    layerMap.set(id, layer)
    while (layers.length <= layer) layers.push([])
    layers[layer].push(id)
    for (const childId of (outEdges.get(id) || [])) {
      const deg = (inDegree.get(childId) || 1) - 1
      inDegree.set(childId, deg)
      if (deg === 0 && !layerMap.has(childId)) queue.push(childId)
    }
  }

  // Position by layer
  const positions: LayoutResult['positions'] = []
  for (let l = 0; l < layers.length; l++) {
    const nodes = layers[l]
    const totalW = nodes.reduce((sum, id) => sum + (penMap.get(id)?.width || 100) + spacing, -spacing)
    let cx = (opts.width || 1200) / 2 - totalW / 2
    const cy = 100 + l * 150
    for (const id of nodes) {
      positions.push({ id, x: cx, y: cy })
      cx += (penMap.get(id)?.width || 100) + spacing
    }
  }
  return { positions }
}

/** Main entry: dispatch to algorithm by name. */
export function autoLayout(
  pens: Pen[],
  lines: Line[],
  opts: LayoutOpts & { algorithm?: string },
): LayoutResult {
  const algo = opts.algorithm || 'grid'
  switch (algo) {
    case 'tree':
      return treeLayout(pens, lines, opts)
    case 'force':
      return forceLayout(pens, lines, opts)
    case 'layered':
      return layeredLayout(pens, lines, opts)
    default:
      return gridLayout(pens, lines, opts)
  }
}
