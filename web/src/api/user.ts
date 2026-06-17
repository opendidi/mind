/**
 * User auth API — login / register / profile / captcha
 */
import http from '@/utils/request'

const API = {
  captcha: '/auth/captcha',
  login: '/auth/login',
  logout: '/auth/logout',
  register: '/auth/register',
  refresh: '/auth/refresh',
  profile: '/auth/profile',
  changePassword: '/auth/change-password',
} as const

/** Get image captcha */
export function apiAuthCaptcha() {
  return http.get(API.captcha)
}

/** Login with FormData */
export function apiLogin(data: FormData) {
  return http.post(API.login, data)
}

/** Logout */
export function apiLogout() {
  return http.post(API.logout)
}

/** Register with FormData */
export function apiRegister(data: FormData) {
  return http.post(API.register, data)
}

/** Refresh access token */
export function apiRefreshToken(data: { refresh_token: string }) {
  return http.post(API.refresh, data)
}

/** Get user profile */
export function apiGetProfile() {
  return http.get(API.profile)
}

/** Update user profile */
export function apiUpdateProfile(data: FormData) {
  return http.put(API.profile, data)
}

/** Change password */
export function apiChangePassword(data: FormData) {
  return http.post(API.changePassword, data)
}
