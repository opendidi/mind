/*
 * @Descripttion:
 * @version: 1.0.0
 * @Author: htang
 * @Date: 2024-10-08 20:13:33
 * @LastEditors: htang
 * @LastEditTime: 2024-10-08 20:13:48
 */
import defaultSettings from '@/settings.ts'

const title = defaultSettings.title || '全景漫游'

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