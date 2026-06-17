/**
 * Chat conversation API — persistence to backend
 */
import http from '@/utils/request'

const API = {
  conversations: '/chat/conversations',
} as const

export interface ChatMsg {
  id: string
  role: 'user' | 'agent' | 'error'
  text?: string
}

/** Get conversation list (without message content) */
export function apiChatList(params?: { limit?: number; offset?: number; keyword?: string }) {
  return http.get(API.conversations, { params })
}

/** Load a single conversation with full messages */
export function apiChatLoad(convId: string, signal?: AbortSignal) {
  return http.get(`${API.conversations}/${convId}`, signal ? { signal } : undefined)
}

/** Save or update a conversation */
export function apiChatSave(data: { id: string; title?: string; messages?: ChatMsg[]; pinned?: boolean }) {
  return http.post(API.conversations, data)
}

/** Delete a conversation */
export function apiChatDelete(convId: string) {
  return http.delete(`${API.conversations}/${convId}`)
}

/** Update message feedback */
export function apiChatFeedback(convId: string, msgId: string, feedback: string, signal?: AbortSignal) {
  return http.patch(`${API.conversations}/${convId}/feedback`, { msg_id: msgId, feedback }, { signal })
}

/** Upload document file for agent analysis */
export function apiChatUploadFile(file: File) {
  const formData = new FormData()
  formData.append('file', file)
  return http.post('/chat/upload', formData).then((res: any) => {
    if (res?.code === 200 && res.data) return res.data
    throw new Error(res?.message || '上传失败')
  })
}
