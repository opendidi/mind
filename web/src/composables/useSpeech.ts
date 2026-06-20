/*
 * TTS 语音朗读 Composable — Web Speech API + ChatTTS 后端
 *
 * 全局状态管理：同一时间只允许一个音频播放，新播放自动停止旧播放。
 */
import { ref, onUnmounted, readonly } from 'vue'
import { requestTTS } from '@/api/agent'

// ── 模块级全局状态（跨组件共享）───────────────────────────────────────────

let globalAudio: HTMLAudioElement | null = null
let globalAbort: AbortController | null = null
let globalLoadingRef: ReturnType<typeof ref<boolean>> | null = null
let globalSpeakingRef: ReturnType<typeof ref<boolean>> | null = null
let globalErrorRef: ReturnType<typeof ref<string>> | null = null

/** 停止全局音频（任意组件调用均可生效） */
function stopGlobal() {
  // 停止浏览器 TTS
  if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
    window.speechSynthesis.cancel()
  }

  // 取消进行中的请求
  if (globalAbort) {
    globalAbort.abort()
    globalAbort = null
  }

  // 停止 ChatTTS 音频
  if (globalAudio) {
    globalAudio.pause()
    globalAudio.currentTime = 0
    globalAudio = null
  }

  // 重置全局状态 refs
  if (globalLoadingRef) globalLoadingRef.value = false
  if (globalSpeakingRef) globalSpeakingRef.value = false
}

// ── composable ────────────────────────────────────────────────────────────

export function useSpeech() {
  const speaking = ref(false)
  const supported = ref(typeof window !== 'undefined' && 'speechSynthesis' in window)
  const loading = ref(false)
  const errorMessage = ref('')

  // ── Web Speech API (browser built-in, instant) ──────────────────────────

  function speak(text: string) {
    if (!supported.value || speaking.value) return

    stopGlobal()
    speaking.value = true

    const clean = text.replace(/<\/?[^>]+(>|$)/g, '').replace(/[#*`~>\[\]|]/g, '').trim()
    if (!clean) {
      speaking.value = false
      return
    }

    const utter = new SpeechSynthesisUtterance(clean)
    utter.rate = 1
    utter.pitch = 1
    utter.onend = () => { speaking.value = false }
    utter.onerror = () => { speaking.value = false }

    window.speechSynthesis.speak(utter)
  }

  // ── ChatTTS backend (higher quality) ────────────────────────────────────

  async function speakChatTTS(text: string): Promise<void> {
    // 停止任何正在播放的音频（包括其他组件的）
    stopGlobal()

    errorMessage.value = ''
    loading.value = true
    globalLoadingRef = loading
    globalSpeakingRef = speaking

    const controller = new AbortController()
    globalAbort = controller

    try {
      const t0 = performance.now()
      const audioUrl = await requestTTS(text, controller.signal)

      const elapsed = ((performance.now() - t0) / 1000).toFixed(1)
      console.log(`[TTS] ChatTTS generated in ${elapsed}s`)

      const audio = new Audio(audioUrl)
      globalAudio = audio
      audio.play()

      audio.onplay = () => {
        loading.value = false
        speaking.value = true
      }
      audio.onended = () => {
        speaking.value = false
        globalAudio = null
        globalSpeakingRef = null
        globalLoadingRef = null
      }
      audio.onerror = () => {
        speaking.value = false
        loading.value = false
        globalAudio = null
        globalSpeakingRef = null
        globalLoadingRef = null
        errorMessage.value = '播放失败'
      }
    } catch (err: any) {
      loading.value = false
      globalLoadingRef = null
      globalSpeakingRef = null
      if (err.name === 'AbortError') return
      errorMessage.value = err.message || 'TTS 生成失败'
      console.error('[TTS] ChatTTS error:', err)
      setTimeout(() => { errorMessage.value = '' }, 3000)
    }
  }

  // ── stop ────────────────────────────────────────────────────────────────

  function stop() {
    stopGlobal()
    speaking.value = false
    loading.value = false
    errorMessage.value = ''
  }

  function stopAll() {
    stop()
  }

  // ── cleanup ─────────────────────────────────────────────────────────────

  onUnmounted(() => {
    // 只有当本组件拥有全局音频时才停止
    if (globalAudio && (speaking.value || loading.value)) {
      stopGlobal()
    }
  })

  return {
    speaking,
    supported: readonly(supported),
    loading: readonly(loading),
    errorMessage: readonly(errorMessage),
    speak,
    speakChatTTS,
    stop,
    stopAll,
  }
}
