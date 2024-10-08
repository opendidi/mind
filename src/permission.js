/*
 * @Descripttion:
 * @version: 1.0.0
 * @Author: htang
 * @Date: 2024-10-08 20:12:03
 * @LastEditors: htang
 * @LastEditTime: 2024-10-08 20:16:22
 */
import router from '@/router'
import getPageTitle from '@/utils/get-page-title.ts'
import NProgress from 'nprogress' // progress bar
import 'nprogress/nprogress.css' // progress bar style

NProgress.configure({ showSpinner: false }) // NProgress Configuration

router.beforeEach(async (to, from, next) => {
  // set page title
  document.title = getPageTitle(to.meta.title)
  // start progress bar
  NProgress.start()
  next()
})

router.afterEach(() => {
  // finish progress bar
  NProgress.done()
})