/**
 * Conversation management Composable — CRUD / pin / pagination / route sync
 */
import { ref, computed, watch, nextTick, type Ref, type ComputedRef } from 'vue'
import { message, Modal } from 'ant-design-vue'
import type { Router, RouteLocationNormalizedLoaded } from 'vue-router'
import { apiChatList, apiChatLoad, apiChatSave, apiChatDelete } from '@/api/chat'
import type { ChatMessage } from './useAgentChat'

export interface Conversation {
  id: string
  title: string
  time: string
  messages?: ChatMessage[]
  pinned?: boolean
}

export interface UseConversationsOptions {
  messages: Ref<ChatMessage[]>
  currentPlan: Ref<{ goal: string; steps: { id: string; desc: string; tool: string | null; confirm: boolean; status?: string }[]; risk: string } | null>
  agentAbort: () => void
  agentClear: () => void
  router: Router
  route: RouteLocationNormalizedLoaded
  onBeforeSwitch?: () => void
  onLoaded?: () => void
}

export interface UseConversationsReturn {
  conversations: Ref<Conversation[]>
  activeConvId: Ref<string>
  hasMoreConversations: Ref<boolean>
  switchingConv: Ref<boolean>
  activeConvTitle: ComputedRef<string>
  saveCurrentConv: () => Promise<string | null>
  /** Save without route changes or error toasts — for auto-save during streaming */
  silentSave: () => Promise<void>
  onNewChat: () => void
  onSwitchConv: (id: string) => Promise<void>
  onDeleteConv: (id: string) => Promise<void>
  onTogglePin: (convId: string) => void
  onLoadMoreConversations: () => Promise<void>
  onExportConv: (convId: string, format: 'json' | 'md') => Promise<void>
  onClearData: () => void
  loadConversationList: (reset?: boolean) => Promise<void>
}

export function useConversations(options: UseConversationsOptions): UseConversationsReturn {
  const { messages, currentPlan, agentAbort, agentClear, router, route, onBeforeSwitch, onLoaded } = options

  const conversations = ref<Conversation[]>([])
  const activeConvId = ref('')
  const hasMoreConversations = ref(false)
  const convPageOffset = ref(0)
  const convPageSize = 30
  const switchingConv = ref(false)
  let saveSeq = 0
  let convLoadCtrl: AbortController | null = null

  const activeConvTitle = computed(() => {
    const conv = conversations.value.find((c) => c.id === activeConvId.value)
    if (conv?.title) return conv.title
    if (messages.value.length > 0) {
      const firstUser = messages.value.find((m) => m.role === 'user')
      return firstUser?.text?.slice(0, 30) || '对话'
    }
    return ''
  })

  function downloadFile(filename: string, content: string, mime: string) {
    const blob = new Blob([content], { type: `${mime};charset=utf-8` })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
    message.success('导出成功')
  }

  async function saveCurrentConv(): Promise<string | null> {
    const seqSnapshot = saveSeq
    const msgs = [...messages.value]
    if (msgs.length === 0) return null
    const firstUser = msgs.find((m) => m.role === 'user')
    const title = firstUser?.text?.slice(0, 30) || '新对话'
    const id = activeConvId.value || crypto.randomUUID()

    if (seqSnapshot !== saveSeq) return null

    try {
      await apiChatSave({ id, title, messages: msgs })
    } catch {
      message.error('保存对话失败')
      return null
    }

    if (seqSnapshot !== saveSeq) return null

    if (!activeConvId.value) {
      activeConvId.value = id
      if (!route.params.id) router.replace({ name: 'chat', params: { id } })
    }

    const existing = conversations.value.find((c) => c.id === id)
    const present = existing?.pinned || false
    const conv: Conversation = { id, title, time: new Date().toLocaleString(), messages: msgs, pinned: present }
    const idx = conversations.value.findIndex((c) => c.id === id)
    if (idx >= 0) conversations.value[idx] = conv
    else conversations.value.unshift(conv)

    return id
  }

  // Silent save — no route manipulation, no error toast. Used for auto-save during streaming.
  async function silentSave() {
    const msgs = [...messages.value]
    if (msgs.length === 0) return
    const firstUser = msgs.find((m) => m.role === 'user')
    const title = firstUser?.text?.slice(0, 30) || '新对话'
    const id = activeConvId.value || crypto.randomUUID()

    try {
      await apiChatSave({ id, title, messages: msgs })
    } catch {
      // Silently ignore — don't distract user during streaming
      return
    }

    if (!activeConvId.value) {
      activeConvId.value = id
      if (!route.params.id) router.replace({ name: 'chat', params: { id } })
    }

    const existing = conversations.value.find((c) => c.id === id)
    const present = existing?.pinned || false
    const conv: Conversation = { id, title, time: new Date().toLocaleString(), messages: msgs, pinned: present }
    const idx = conversations.value.findIndex((c) => c.id === id)
    if (idx >= 0) conversations.value[idx] = conv
    else conversations.value.unshift(conv)
  }

  async function loadConversationList(reset = true) {
    try {
      const res = await apiChatList({ limit: convPageSize, offset: reset ? 0 : convPageOffset.value })
      if (res?.code === 200 && res.data) {
        const mapped = res.data.map((r: { id: string; title: string; time: string; pinned?: boolean }) => ({
          id: r.id,
          title: r.title || '',
          time: r.time || '',
          messages: [],
          pinned: r.pinned || false,
        }))
        conversations.value = reset ? mapped : [...conversations.value, ...mapped]
        hasMoreConversations.value = res.data.length >= convPageSize
        convPageOffset.value = reset ? res.data.length : convPageOffset.value + res.data.length
      }
    } catch {
      /* network error, skip */
    }
  }

  async function onLoadMoreConversations() {
    await loadConversationList(false)
  }

  function onNewChat() {
    if (messages.value.length > 0) saveCurrentConv()
    router.push({ name: 'chat' })
  }

  async function onSwitchConv(id: string) {
    const conv = conversations.value.find((c) => c.id === id)
    if (!conv || conv.id === activeConvId.value) return
    agentAbort()
    if (messages.value.length > 0) await saveCurrentConv()
    router.push({ name: 'chat', params: { id: conv.id } })
  }

  async function onDeleteConv(id: string) {
    if (activeConvId.value === id) {
      activeConvId.value = ''
      messages.value = []
      currentPlan.value = null
      router.replace({ name: 'chat' })
    }
    conversations.value = conversations.value.filter((c) => c.id !== id)
    try {
      await apiChatDelete(id)
    } catch (e: any) {
      message.error(e?.message || '删除对话失败')
    }
  }

  function onTogglePin(convId: string) {
    const conv = conversations.value.find((c) => c.id === convId)
    if (!conv) return
    conv.pinned = !conv.pinned
    apiChatSave({ id: convId, pinned: conv.pinned }).catch(() => message.error('置顶操作失败'))
  }

  async function onExportConv(convId: string, format: 'json' | 'md') {
    let msgs: ChatMessage[] = []
    let title = '对话'

    if (convId === activeConvId.value) {
      msgs = [...messages.value]
      title = activeConvTitle.value || '对话'
    } else {
      try {
        const res = await apiChatLoad(convId)
        if (res?.code === 200 && res.data?.messages) {
          msgs = res.data.messages
          title = res.data.title || '对话'
        }
      } catch {
        message.error('加载对话失败')
        return
      }
    }

    if (msgs.length === 0) return
    const timestamp = new Date().toISOString().slice(0, 10)

    if (format === 'md') {
      let md = `# ${title}\n\n> 导出时间: ${new Date().toLocaleString()}\n\n---\n\n`
      for (const m of msgs) {
        if (m.role === 'user') {
          md += `**用户:** ${m.text || ''}\n\n`
          if (m.images?.length) m.images.forEach((u, i) => { md += `![图片${i + 1}](${u})\n\n` })
          if (m.files?.length) m.files.forEach((f) => { md += `- 附件: ${f.name}\n` })
        } else if (m.role === 'agent') {
          md += `**AI:** ${m.text || ''}\n\n`
        } else if (m.role === 'tool' && m.tool) {
          md += `**工具 [${m.tool.name}]:** ${m.tool.success ? '完成' : '失败'}\n\n`
        } else if (m.role === 'error') {
          md += `**错误:** ${m.text || ''}\n\n`
        }
      }
      downloadFile(`${title}-${timestamp}.md`, md, 'text/markdown')
    } else {
      const json = JSON.stringify(msgs, null, 2)
      downloadFile(`${title}-${timestamp}.json`, json, 'application/json')
    }
  }

  function onClearData() {
    if (conversations.value.length === 0 && messages.value.length === 0) {
      message.info('没有可清空的对话')
      return
    }
    Modal.confirm({
      title: '确认清空',
      content: `将清空全部历史对话记录（共 ${conversations.value.length} 个会话），此操作不可恢复，确定要继续吗？`,
      okText: '确定清空全部',
      cancelText: '取消',
      onOk: async () => {
        saveSeq++
        activeConvId.value = ''
        messages.value = []
        currentPlan.value = null
        agentClear()

        const ids = conversations.value.map((c) => c.id)
        conversations.value = []

        const results = await Promise.allSettled(ids.map((id) => apiChatDelete(id)))
        const failed = results.filter((r) => r.status === 'rejected').length
        router.push({ name: 'chat' })
        message.success(failed === 0 ? '已清空全部历史会话' : `已清空（${failed} 个删除失败）`)
      },
    })
  }

  // Route → conversation loading
  watch(
    () => route.params.id as string | undefined,
    async (newId, oldId) => {
      if (newId === activeConvId.value) return
      agentAbort()
      convLoadCtrl?.abort()
      onBeforeSwitch?.()
      if (oldId && messages.value.length > 0) await saveCurrentConv()
      if (newId) {
        messages.value = []
        currentPlan.value = null
        switchingConv.value = true
        const ctrl = new AbortController()
        convLoadCtrl = ctrl
        try {
          const res = await apiChatLoad(newId, ctrl.signal)
          if (res?.code === 200 && res.data) {
            activeConvId.value = newId
            messages.value = res.data.messages || []
            await nextTick()
            onLoaded?.()
          } else {
            router.replace({ name: 'chat' })
          }
        } catch (err: any) {
          if (err?.name === 'AbortError' || err?.code === 'ERR_CANCELED') return
          router.replace({ name: 'chat' })
        } finally {
          if (convLoadCtrl === ctrl) switchingConv.value = false
        }
      } else {
        activeConvId.value = ''
        messages.value = []
        currentPlan.value = null
      }
    },
    { immediate: true },
  )

  return {
    conversations,
    activeConvId,
    hasMoreConversations,
    switchingConv,
    activeConvTitle,
    saveCurrentConv,
    silentSave,
    onNewChat,
    onSwitchConv,
    onDeleteConv,
    onTogglePin,
    onLoadMoreConversations,
    onExportConv,
    onClearData,
    loadConversationList,
  }
}
