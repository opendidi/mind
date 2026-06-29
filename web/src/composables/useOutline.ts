/**
 * useOutline — Extract Markdown headings from rendered chat messages,
 * build a grouped tree, search/filter, and debounce during streaming.
 */
import { ref, computed, watch, type Ref } from 'vue'
import type { ChatMessage } from './useAgentChat'

export interface Heading {
  id: string
  text: string
  level: number
  msgId: string
  children: Heading[]
  el: HTMLElement
}

export interface OutlineGroup {
  msgId: string
  msgSummary: string
  msgIndex: number
  headings: Heading[]
}

const HEADING_SELECTOR = '.md-body h1, .md-body h2, .md-body h3, .md-body h4, .md-body h5, .md-body h6'

export function useOutline(messages: Ref<ChatMessage[]>, loading: Ref<boolean>) {
  const groups = ref<OutlineGroup[]>([])
  const searchQuery = ref('')
  const collapsedGroups = ref<Set<string>>(new Set())

  // ── Extract headings from DOM ──────────────────────────────

  function extractHeadings(): OutlineGroup[] {
    const result: OutlineGroup[] = []
    const agentMsgs = messages.value.filter(m => m.role === 'agent' && m.text)

    for (let gi = 0; gi < agentMsgs.length; gi++) {
      const msg = agentMsgs[gi]
      const container = document.querySelector(`[data-msg-id="${msg.id}"]`)
      if (!container) continue

      const headingEls = container.querySelectorAll(HEADING_SELECTOR) as NodeListOf<HTMLElement>
      if (headingEls.length === 0) continue

      const flat: Heading[] = []
      headingEls.forEach((el, hi) => {
        const level = parseInt(el.tagName.charAt(1), 10)
        const text = el.textContent?.trim() || ''
        if (!text) return

        // Ensure heading has an id for scroll-to
        let id = el.id
        if (!id) {
          id = `h-${msg.id}-${hi}`
          el.id = id
        }

        flat.push({ id, text, level, msgId: msg.id, children: [], el })
      })

      if (flat.length === 0) continue

      // Build tree from flat list
      const tree = buildTree(flat)

      // Message summary: first 60 chars of text without markdown syntax
      const plainText = (msg.text || '').replace(/[#*`>\[\]()!_~]/g, '').trim()
      const msgSummary = plainText.slice(0, 60) + (plainText.length > 60 ? '…' : '')

      result.push({
        msgId: msg.id,
        msgSummary,
        msgIndex: gi + 1,
        headings: tree,
      })
    }

    return result
  }

  function buildTree(flat: Heading[]): Heading[] {
    const roots: Heading[] = []
    const stack: Heading[] = []

    for (const h of flat) {
      // Pop stack until we find a parent with level < current
      while (stack.length > 0 && stack[stack.length - 1].level >= h.level) {
        stack.pop()
      }

      if (stack.length === 0) {
        roots.push(h)
      } else {
        stack[stack.length - 1].children.push(h)
      }
      stack.push(h)
    }

    return roots
  }

  // ── Debounced refresh ──────────────────────────────────────

  let debounceTimer: ReturnType<typeof setTimeout> | null = null
  let rafId: ReturnType<typeof requestAnimationFrame> | null = null

  function refresh() {
    // Cancel pending debounce
    if (debounceTimer) {
      clearTimeout(debounceTimer)
      debounceTimer = null
    }

    const delay = loading.value ? 300 : 50

    debounceTimer = setTimeout(() => {
      // Use rAF to ensure DOM is painted
      if (rafId) cancelAnimationFrame(rafId)
      rafId = requestAnimationFrame(() => {
        groups.value = extractHeadings()
      })
    }, delay)
  }

  // ── Search filter ──────────────────────────────────────────

  function filterGroup(group: OutlineGroup, query: string): OutlineGroup | null {
    const q = query.toLowerCase()

    function filterHeadings(headings: Heading[]): Heading[] {
      const result: Heading[] = []
      for (const h of headings) {
        const childMatches = filterHeadings(h.children)
        const selfMatches = h.text.toLowerCase().includes(q)
        if (selfMatches || childMatches.length > 0) {
          result.push({ ...h, children: childMatches })
        }
      }
      return result
    }

    const filtered = filterHeadings(group.headings)
    if (filtered.length > 0 || group.msgSummary.toLowerCase().includes(q)) {
      return { ...group, headings: filtered.length > 0 ? filtered : group.headings }
    }
    return null
  }

  const filteredGroups = computed(() => {
    const q = searchQuery.value.trim()
    if (!q) return groups.value
    return groups.value.map(g => filterGroup(g, q)).filter(Boolean) as OutlineGroup[]
  })

  // ── Watch for message changes ──────────────────────────────

  watch(
    () => messages.value,
    () => refresh(),
    { deep: true, immediate: false },
  )

  // Also refresh on loading end (final state)
  watch(
    () => loading.value,
    (val) => {
      if (!val) refresh()
    },
  )

  // ── Public API ─────────────────────────────────────────────

  function toggleGroup(msgId: string) {
    const s = new Set(collapsedGroups.value)
    if (s.has(msgId)) {
      s.delete(msgId)
    } else {
      s.add(msgId)
    }
    collapsedGroups.value = s
  }

  function scrollToHeading(heading: Heading) {
    heading.el.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }

  /** Force immediate refresh (call after manual DOM changes) */
  function forceRefresh() {
    if (debounceTimer) clearTimeout(debounceTimer)
    if (rafId) cancelAnimationFrame(rafId)
    groups.value = extractHeadings()
  }

  return {
    groups,
    filteredGroups,
    searchQuery,
    collapsedGroups,
    toggleGroup,
    scrollToHeading,
    refresh,
    forceRefresh,
  }
}
