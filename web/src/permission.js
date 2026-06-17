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
  NProgress.start()
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

router.afterEach(() => {
  NProgress.done()
})
