/*
 * @Descripttion:
 * @version: 1.0.0
 * @Author: htang
 * @Date: 2024-10-08 20:13:33
 * @LastEditors: htang
 * @LastEditTime: 2024-10-08 20:30:05
 */
import defaultSettings from '@/settings.ts'

const title = defaultSettings.title || '图形可视化编辑器'

/**
 * @param {String} pageTitle
 * @returns
 */
export default function getPageTitle(pageTitle) {
  if (pageTitle) {
    return `${pageTitle} - ${title}`
  }
  return `${title}`
}