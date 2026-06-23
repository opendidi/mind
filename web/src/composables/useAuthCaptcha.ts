/**
 * Auth captcha composable — shared by login and register pages
 */
import { ref, reactive, onMounted } from 'vue'
import { apiAuthCaptcha } from '@/api/user'

export function useAuthCaptcha() {
  const randCodeData = reactive({
    captcha_id: '',
    randCodeImage: '',
    requestCodeSuccess: false,
  })
  let initTimer: ReturnType<typeof setTimeout> | null = null

  function initAuthCaptcha() {
    if (initTimer) clearTimeout(initTimer)
    initTimer = setTimeout(async () => {
      try {
        const res = await apiAuthCaptcha()
        if (res?.code === 200 && res.data) {
          randCodeData.requestCodeSuccess = true
          randCodeData.captcha_id = res.data.captcha_id
          randCodeData.randCodeImage = res.data.captcha_image
        }
      } catch {
        /* ignore */
      }
      initTimer = null
    }, 500)
  }

  onMounted(() => {
    initAuthCaptcha()
  })

  return { randCodeData, initAuthCaptcha }
}
