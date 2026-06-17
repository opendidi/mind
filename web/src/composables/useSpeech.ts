/*
 * TTS 语音朗读 Composable — Web Speech API
 */
import { ref, onUnmounted } from 'vue'

export function useSpeech() {
  const speaking = ref(false)
  const supported = ref(typeof window !== 'undefined' && 'speechSynthesis' in window)

  function speak(text: string) {
    if (!supported.value || speaking.value) return

    window.speechSynthesis.cancel()

    const clean = text.replace(/<\/?[^>]+(>|$)/g, '').replace(/[#*`~>\[\]|]/g, '').trim()
    if (!clean) return

    const utter = new SpeechSynthesisUtterance(clean)
    utter.rate = 1
    utter.pitch = 1
    utter.onstart = () => { speaking.value = true }
    utter.onend = () => { speaking.value = false }
    utter.onerror = () => { speaking.value = false }

    window.speechSynthesis.speak(utter)
  }

  function stop() {
    window.speechSynthesis.cancel()
    speaking.value = false
  }

  onUnmounted(() => {
    window.speechSynthesis.cancel()
  })

  return { speaking, supported, speak, stop }
}
