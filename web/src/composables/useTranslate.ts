import { ref } from 'vue'

export function useTranslate(messageText: string, messageId: string) {
  const loading = ref(false)
  const error = ref('')
  const result = ref('')
  const engine = ref('')
  const srcLang = ref('')
  const tgtLang = ref('zh')
  const pos = ref<{ x: number; y: number } | null>(null)
  const style = ref('general')
  let text = ''
  let abortController: AbortController | null = null

  async function translate(targetLang?: string) {
    let sel = window.getSelection()?.toString().trim()
    if (!sel) sel = messageText || ''
    if (!sel) return
    text = sel
    abortController?.abort()
    abortController = new AbortController()
    const target = targetLang || (/[一-龥]/.test(text) ? 'en' : 'zh')
    loading.value = true
    error.value = ''
    result.value = ''
    try {
      const { translateText } = await import('@/api/translate')
      const res = await translateText({ text, target_lang: target, source_lang: 'auto', style: style.value, signal: abortController.signal })
      result.value = res.translated
      engine.value = res.engine
      srcLang.value = res.source_lang
      tgtLang.value = res.target_lang
    } catch (e: any) {
      if (e?.name === 'AbortError' || e?.name === 'CanceledError') return
      error.value = e.message || '翻译失败'
    } finally {
      loading.value = false
    }
  }

  function showPopover() {
    const sel = window.getSelection()
    if (sel?.rangeCount && sel.toString().trim()) {
      const rect = sel.getRangeAt(0).getBoundingClientRect()
      pos.value = { x: rect.left + rect.width / 2 - 170, y: rect.bottom }
    } else {
      const el = document.querySelector(`[data-msg-id="${messageId}"] .msg-bubble`)
      if (el) {
        const rect = el.getBoundingClientRect()
        pos.value = { x: rect.left + 16, y: rect.bottom + 4 }
      } else {
        pos.value = { x: window.innerWidth / 2 - 170, y: window.innerHeight / 3 }
      }
    }
    translate()
  }

  async function changeTarget(lang: string) {
    tgtLang.value = lang
    abortController?.abort()
    abortController = new AbortController()
    loading.value = true
    error.value = ''
    result.value = ''
    try {
      const { translateText } = await import('@/api/translate')
      const res = await translateText({ text, target_lang: lang, source_lang: 'auto', style: style.value, signal: abortController.signal })
      result.value = res.translated
      engine.value = res.engine
      srcLang.value = res.source_lang
      tgtLang.value = res.target_lang
    } catch (e: any) {
      if (e?.name === 'AbortError' || e?.name === 'CanceledError') return
      error.value = e.message || '翻译失败'
    } finally {
      loading.value = false
    }
  }

  async function changeStyle(s: string) {
    style.value = s
    abortController?.abort()
    abortController = new AbortController()
    loading.value = true
    error.value = ''
    result.value = ''
    try {
      const { translateText } = await import('@/api/translate')
      const target = tgtLang.value || 'zh'
      const res = await translateText({ text, target_lang: target, source_lang: 'auto', style: s, signal: abortController.signal })
      result.value = res.translated
      engine.value = res.engine
      srcLang.value = res.source_lang
      tgtLang.value = res.target_lang
    } catch (e: any) {
      if (e?.name === 'AbortError' || e?.name === 'CanceledError') return
      error.value = e.message || '翻译失败'
    } finally {
      loading.value = false
    }
  }

  function close() {
    abortController?.abort()
    abortController = null
    pos.value = null
    text = ''
    style.value = 'general'
    loading.value = false
    error.value = ''
    result.value = ''
    engine.value = ''
    srcLang.value = ''
  }

  return {
    loading,
    error,
    result,
    engine,
    srcLang,
    tgtLang,
    pos,
    style,
    translate,
    showPopover,
    changeTarget,
    changeStyle,
    close,
  }
}
