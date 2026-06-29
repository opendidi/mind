/**
 * useActiveHeading — IntersectionObserver-based active heading tracking.
 *
 * Watches all heading elements in the message area and determines
 * which one is currently most visible to the user.
 */
import { ref, onMounted, onBeforeUnmount, type Ref } from 'vue'

const HEADING_SELECTOR = '.md-body h1, .md-body h2, .md-body h3, .md-body h4, .md-body h5, .md-body h6'

export function useActiveHeading(scrollContainerRef: Ref<HTMLElement | null | undefined>) {
  const activeId = ref<string | null>(null)

  let observer: IntersectionObserver | null = null

  // Track all observed headings with their visibility ratio
  const visibleHeadings = new Map<string, number>()

  function setupObserver() {
    teardownObserver()

    observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          const id = entry.target.id
          if (!id) continue

          if (entry.isIntersecting) {
            visibleHeadings.set(id, entry.intersectionRatio)
          } else {
            visibleHeadings.delete(id)
          }
        }

        // Pick the heading with highest intersection ratio
        if (visibleHeadings.size > 0) {
          let bestId = ''
          let bestRatio = 0
          for (const [id, ratio] of visibleHeadings) {
            if (ratio > bestRatio) {
              bestRatio = ratio
              bestId = id
            }
          }
          activeId.value = bestId
        }
      },
      {
        root: scrollContainerRef.value || null,
        rootMargin: '-10% 0px -70% 0px', // Top 10% zone — heading near top of viewport
        threshold: [0, 0.25, 0.5, 0.75, 1],
      },
    )

    // Observe all existing headings
    const headings = document.querySelectorAll(HEADING_SELECTOR)
    headings.forEach(el => {
      if (el.id) observer!.observe(el)
    })
  }

  function teardownObserver() {
    if (observer) {
      observer.disconnect()
      observer = null
    }
    visibleHeadings.clear()
  }

  /** Call after new headings appear in DOM (e.g., after streaming) */
  function refresh() {
    if (!observer) return
    // Re-observe — disconnect and reconnect to pick up new headings
    teardownObserver()
    setupObserver()
  }

  onMounted(() => {
    setupObserver()
  })

  onBeforeUnmount(() => {
    teardownObserver()
  })

  return {
    activeId,
    refresh,
  }
}
