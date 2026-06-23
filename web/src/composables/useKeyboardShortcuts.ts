import { onMounted, onUnmounted } from 'vue'
import type { Meta2d } from '@meta2d/core'

export function useKeyboardShortcuts(meta2d: Meta2d) {
  function handleKeyDown(e: KeyboardEvent) {
    // Don't intercept when focus is in an input
    const tag = (e.target as HTMLElement)?.tagName
    if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return

    const ctrl = e.ctrlKey || e.metaKey

    if (e.key === 'Delete' || e.key === 'Backspace') {
      e.preventDefault()
      meta2d.delete()
      return
    }

    if (ctrl && e.key === 'c') {
      e.preventDefault()
      document.execCommand('copy')
      return
    }

    if (ctrl && e.key === 'v') {
      e.preventDefault()
      document.execCommand('paste')
      return
    }

    if (ctrl && e.key === 'a') {
      e.preventDefault()
      meta2d.activeAll()
      return
    }

    if (ctrl && e.key === 'd') {
      e.preventDefault()
      const selected = (meta2d.store as any).active || []
      if (selected.length) {
        const cloneData = meta2d.data()
        const selectedPens = ((cloneData as any).pens || []).filter((p: any) => selected.includes(p.id))
        selectedPens.forEach((p: any) => {
          meta2d.addPen({ ...p, id: undefined, x: (p.x || 0) + 20, y: (p.y || 0) + 20 })
        })
      }
      return
    }

    // Ctrl+Z/Y/S — Meta2D handles Ctrl+Z/Y natively; Ctrl+S for save
    if (ctrl && (e.key === 'z' || e.key === 'Z' || e.key === 'y' || e.key === 'Y')) {
      return
    }

    if (ctrl && e.key === 's') {
      e.preventDefault()
      return // Save handled by Header component
    }

    const step = e.shiftKey ? 10 : 1
    switch (e.key) {
      case 'ArrowUp':
        e.preventDefault()
        moveActive(meta2d, 0, -step)
        break
      case 'ArrowDown':
        e.preventDefault()
        moveActive(meta2d, 0, step)
        break
      case 'ArrowLeft':
        e.preventDefault()
        moveActive(meta2d, -step, 0)
        break
      case 'ArrowRight':
        e.preventDefault()
        moveActive(meta2d, step, 0)
        break
      case 'Escape':
        e.preventDefault()
        ;(meta2d.store as any).active = []
        ;(meta2d as any).drawLinePencil = null
        meta2d.render()
        break
    }
  }

  function moveActive(m: Meta2d, dx: number, dy: number) {
    const active = (m.store as any).active || []
    if (!active.length) return
    const data = m.data() as any
    const pens = data.pens || []
    for (const pen of pens) {
      if (active.includes(pen.id)) {
        pen.x = (pen.x || 0) + dx
        pen.y = (pen.y || 0) + dy
        m.setValue({ id: pen.id, x: pen.x, y: pen.y }, { render: false })
      }
    }
    m.render()
  }

  onMounted(() => document.addEventListener('keydown', handleKeyDown))
  onUnmounted(() => document.removeEventListener('keydown', handleKeyDown))
}
