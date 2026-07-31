/**
 * Axios request instance — auth headers + auto token refresh
 */
import axios from 'axios'
import { message } from 'ant-design-vue'
import { getCache, setCache, removeCache } from '@/utils/auth'

const instance = axios.create({
  baseURL: import.meta.env.VITE_GLOB_API_URL as string,
  timeout: 100000,
})

// Token refresh state (avoid concurrent refreshes)
let isRefreshing = false
let pendingRequests: Array<(token: string) => void> = []

function resolvePendingRequests(token: string) {
  pendingRequests.forEach(cb => cb(token))
  pendingRequests = []
}

function rejectPendingRequests() {
  pendingRequests = []
}

async function tryRefreshToken(): Promise<string | null> {
  const refreshToken = getCache<string>('refresh-token')
  if (!refreshToken) return null

  try {
    const res = await axios.post(`${import.meta.env.VITE_GLOB_API_URL}/auth/refresh`, { refresh_token: refreshToken })
    if (res.data?.code === 200 && res.data?.data) {
      const { access_token, refresh_token } = res.data.data
      setCache('auth-token', access_token)
      setCache('refresh-token', refresh_token)
      return access_token
    }
  } catch {
    console.warn('Token refresh request failed')
  }
  return null
}

// Request interceptor — attach auth token
instance.interceptors.request.use(
  function (config: any) {
    const token = getCache<string>('auth-token')
    if (token) {
      config.headers = config.headers || {}
      config.headers['Authorization'] = `Bearer ${token}`
    }
    config.headers = config.headers || {}
    config.headers['X-Requested-With'] = 'XMLHttpRequest'
    return config
  },
  function (error) {
    return Promise.reject(error)
  },
)

// Response interceptor — handle 401 auto-refresh
instance.interceptors.response.use(
  function (response: any) {
    const { code } = response.data || {}
    const msg = response.data?.message
    switch (code) {
      case 500:
        message.error(msg)
        return Promise.reject(new Error(msg))
      case 401:
        // Handled below in error interceptor (HTTP 401 status)
        break
      case 200:
        return response.data
    }
    return response.data
  },
  async function (error) {
    const { config, response } = error
    const status = response?.status

    // Handle 401 Unauthorized
    if (status === 401 && config && !config._retry) {
      // Don't refresh if this is already a refresh or login request
      const isAuthRequest = config.url?.includes('/auth/refresh') || config.url?.includes('/auth/login')
      if (isAuthRequest) {
        return Promise.reject(error)
      }

      if (!isRefreshing) {
        isRefreshing = true
        config._retry = true

        const newToken = await tryRefreshToken()

        if (newToken) {
          resolvePendingRequests(newToken)
          isRefreshing = false
          // Retry original request with new token
          config.headers = config.headers || {}
          config.headers['Authorization'] = `Bearer ${newToken}`
          return instance(config)
        }

        rejectPendingRequests()
        isRefreshing = false
      } else {
        // Wait for the ongoing refresh to complete
        return new Promise(resolve => {
          pendingRequests.push((token: string) => {
            config.headers = config.headers || {}
            config.headers['Authorization'] = `Bearer ${token}`
            resolve(instance(config))
          })
        })
      }

      // Refresh failed — clear auth and redirect
      removeCache('auth-token')
      removeCache('refresh-token')
      removeCache('user-info')
      message.error('登录已过期，请重新登录')
      window.location.hash = '#/login'
      return Promise.reject(error)
    }

    // Handle other HTTP errors
    switch (status) {
      case 400:
        message.error(response?.data?.message || '请求参数错误')
        break
      case 403:
        message.error('没有权限访问')
        break
      case 408:
        message.error('请求超时')
        break
      case 429:
        message.error('请求过于频繁，请稍后重试')
        break
      case 500:
        message.error(response?.data?.message || '服务器内部错误')
        break
    }
    return Promise.reject(error)
  },
)

export default instance
