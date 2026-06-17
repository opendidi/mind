/**
 * Scroll-to-bottom Composable — RAF-throttled scroll + near-bottom detection
 */
import { ref, watch, type Ref } from 'vue'

export function useScrollToBottom(messages: Ref<readonly unknown[]>, loading: Ref<boolean>) {
  const msgListRef = ref<HTMLElement | null>(null)
  const msgEndRef = ref<HTMLElement | null>(null)
  const isNearBottom = ref(true)
  let scrollRaf = 0

  function scrollToBottom(smooth = false) {
    const el = msgListRef.value
    if (!el) return
    if (smooth) {
      el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' })
    } else {
      el.scrollTop = el.scrollHeight
    }
  }

  function onMsgAreaScroll() {
    const el = msgListRef.value
    if (!el) return
    isNearBottom.value = el.scrollHeight - el.scrollTop - el.clientHeight < 80
  }

  watch(
    () => [messages.value.length, (messages.value[messages.value.length - 1] as any)?.text] as const,
    () => {
      if (!isNearBottom.value) return
      if (scrollRaf) return
      scrollRaf = requestAnimationFrame(() => {
        scrollToBottom()
        scrollRaf = 0
      })
    },
    { flush: 'sync' },
  )

  watch(loading, (val, prev) => {
    if (prev && !val) scrollToBottom(true)
  })

  return { msgListRef, msgEndRef, isNearBottom, scrollToBottom, onMsgAreaScroll }
}
