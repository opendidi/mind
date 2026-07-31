/**
 * User auth store — login / logout / profile management
 */
import { defineStore } from 'pinia'
import { store } from '@/store'
import { getCache, setCache, removeCache } from '@/utils/auth'
import { apiLogin, apiLogout, apiGetProfile, apiUpdateProfile, apiChangePassword } from '@/api/user'

interface UserInfo {
  id?: string
  username?: string
  email?: string
  is_active?: number
  created_at?: string
  last_login?: string
}

interface UserState {
  token: string
  refreshToken: string
  userInfo: UserInfo | null
}

export const useUserStore = defineStore('app-auth-token', {
  state: (): UserState => ({
    token: getCache('auth-token') || '',
    refreshToken: getCache('refresh-token') || '',
    userInfo: getCache('user-info') || null,
  }),

  getters: {
    getToken(state): string {
      if (!state.token) return ''
      // Check JWT expiration
      try {
        const payload = JSON.parse(atob(state.token.split('.')[1]))
        if (payload.exp * 1000 < Date.now()) return ''
      } catch {
        console.warn('Failed to parse JWT token payload for expiration check')
        return ''
      }
      return state.token
    },
    getUserInfo(state): UserInfo | null {
      return state.userInfo
    },
  },

  actions: {
    async login(data: { username: string; password: string; captcha: string; captcha_id: string }) {
      const formData = new FormData()
      formData.append('username', data.username)
      formData.append('password', data.password)
      formData.append('captcha', data.captcha)
      formData.append('captcha_id', data.captcha_id)

      const res = await apiLogin(formData)
      const { access_token, refresh_token, id, email, username } = res.data

      this.token = access_token
      this.refreshToken = refresh_token
      setCache('auth-token', access_token)
      setCache('refresh-token', refresh_token)

      const info: UserInfo = { id, email, username }
      this.userInfo = info
      setCache('user-info', info)
    },

    async logout() {
      try {
        await apiLogout()
      } catch {
        console.warn('Logout API call failed, clearing local auth state anyway')
      }
      this.token = ''
      this.refreshToken = ''
      this.userInfo = null
      removeCache('auth-token')
      removeCache('refresh-token')
      removeCache('user-info')
    },

    async fetchProfile() {
      const res = await apiGetProfile()
      if (res.data) {
        this.userInfo = { ...this.userInfo, ...res.data }
        setCache('user-info', this.userInfo)
      }
    },

    async updateProfile(data: { email?: string }) {
      const formData = new FormData()
      if (data.email) formData.append('email', data.email)
      await apiUpdateProfile(formData)
      await this.fetchProfile()
    },

    async changePassword(data: { old_password: string; new_password: string }) {
      const formData = new FormData()
      formData.append('old_password', data.old_password)
      formData.append('new_password', data.new_password)
      await apiChangePassword(formData)
      return true
    },
  },
})

export function useUserStoreWithOut() {
  return useUserStore(store)
}
