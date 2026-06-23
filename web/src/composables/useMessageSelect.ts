/**
 * Message multi-select Composable — turn-level selection + batch delete
 */
import { ref, type Ref } from 'vue'
import type { ChatMessage } from './useAgentChat'

export function useMessageSelect(messages: Ref<ChatMessage[]>, onChanged: () => void) {
  const selectMode = ref(false)
  const selectedIds = ref(new Set<string>())

  function getTurnRange(idx: number): { start: number; end: number } {
    let start = idx
    while (start > 0 && messages.value[start - 1].role !== 'user') start--
    let end = idx
    while (end < messages.value.length - 1 && messages.value[end + 1].role !== 'user') end++
    return { start, end }
  }

  function onToggleSelect(msgId: string) {
    const idx = messages.value.findIndex(m => m.id === msgId)
    if (idx === -1) return
    const { start, end } = getTurnRange(idx)
    const ids = messages.value.slice(start, end + 1).map(m => m.id)
    const adding = !selectedIds.value.has(msgId)
    const next = new Set(selectedIds.value)
    ids.forEach(id => (adding ? next.add(id) : next.delete(id)))
    selectedIds.value = next
  }

  function onStartSelect(msgId: string) {
    selectMode.value = true
    onToggleSelect(msgId)
  }

  function onSelectAll() {
    selectedIds.value = new Set(messages.value.map(m => m.id))
  }

  function onCancelSelect() {
    selectMode.value = false
    selectedIds.value = new Set()
  }

  function onBatchDelete() {
    if (selectedIds.value.size === 0) return
    const ids = selectedIds.value
    messages.value = messages.value.filter(m => !ids.has(m.id))
    selectedIds.value = new Set()
    selectMode.value = false
    onChanged()
  }

  return {
    selectMode,
    selectedIds,
    onToggleSelect,
    onStartSelect,
    onSelectAll,
    onCancelSelect,
    onBatchDelete,
  }
}
