/**
 * Router permission guard — auth check + page title
 */
import router from '@/router'
import { getCache } from '@/utils/auth'
import getPageTitle from '@/utils/get-page-title.ts'
import NProgress from 'nprogress'
import 'nprogress/nprogress.css'

NProgress.configure({ showSpinner: false })

// Public routes that don't require authentication
const whiteList = ['/login', '/register']
const publicPaths = ['/preview']

function isWhiteListed(path) {
  return whiteList.includes(path) || publicPaths.some((p) => path.startsWith(p))
}

router.beforeEach(async (to, from, next) => {
  // Skip progress bar for same-route chat navigation (avoids scrollbar flash)
  const isChatInternal = to.name === 'chat' && from.name === 'chat'
  if (!isChatInternal) NProgress.start()
  document.title = getPageTitle(to.meta?.title)

  const hasToken = getCache('auth-token')

  if (hasToken) {
    if (to.path === '/login') {
      next({ path: '/' })
      NProgress.done()
    } else {
      next()
    }
  } else {
    if (isWhiteListed(to.path)) {
      next()
    } else {
      next(`/login?redirect=${to.path}`)
      NProgress.done()
    }
  }
})

router.afterEach((to, from) => {
  if (to.name === 'chat' && from.name === 'chat') return
  NProgress.done()
})
