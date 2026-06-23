/**
 * Image attachment upload composable — upload to material API
 */
import { ref, onUnmounted } from 'vue'
import { message } from 'ant-design-vue'
import http from '@/utils/request'

export interface AttachItem {
  name: string
  url: string
  preview: string
  uploading: boolean
  failed: boolean
  file?: File
}

export function useAttachments() {
  const attachments = ref<AttachItem[]>([])

  async function onFileChange(e: Event) {
    const input = e.target as HTMLInputElement
    const files = input.files
    if (!files || files.length === 0) return

    for (let i = 0; i < files.length; i++) {
      const file = files[i]
      if (!file.type.startsWith('image/')) continue

      const preview = URL.createObjectURL(file)
      const item: AttachItem = {
        name: file.name,
        url: '',
        preview,
        uploading: true,
        failed: false,
        file,
      }
      attachments.value.push(item)
      const idx = attachments.value.length - 1

      try {
        const formData = new FormData()
        formData.append('file', file)
        formData.append('type', 'image')

        const res = await http.post('/material/upload', formData)

        const body = res as unknown as { code: number; data: any; message: string }
        if (body?.code === 200 && body.data) {
          const uploaded = Array.isArray(body.data) ? body.data[0] : body.data
          const url = uploaded?.url || ''
          if (url) {
            attachments.value[idx].url = url
            attachments.value[idx].uploading = false
          } else {
            throw new Error('未获取到图片URL')
          }
        } else {
          throw new Error(body?.message || '上传失败')
        }
      } catch (err: any) {
        attachments.value[idx].failed = true
        attachments.value[idx].uploading = false
        if (err?.message && !err?.response) {
          message.error(err.message)
        }
      }
    }

    input.value = ''
  }

  function onRemoveAttachment(idx: number) {
    const att = attachments.value[idx]
    if (att?.preview && att.preview.startsWith('blob:')) {
      URL.revokeObjectURL(att.preview)
    }
    attachments.value.splice(idx, 1)
  }

  function cleanup() {
    attachments.value.forEach(a => {
      if (a.preview?.startsWith('blob:')) URL.revokeObjectURL(a.preview)
    })
    attachments.value = []
  }

  onUnmounted(cleanup)

  return { attachments, onFileChange, onRemoveAttachment, cleanup }
}
