import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import FileCard from '@/components/chat/FileCard.vue'

describe('FileCard.vue', () => {
  it('renders file list', () => {
    const files = [
      { name: 'photo.jpg', url: 'http://example.com/photo.jpg', type: 'image', extension: 'jpg', size: 1024 },
      { name: 'doc.pdf', url: 'http://example.com/doc.pdf', type: 'document', extension: 'pdf', size: 2048 },
    ]

    const wrapper = mount(FileCard, {
      props: { files },
    })

    expect(wrapper.text()).toContain('photo.jpg')
    expect(wrapper.text()).toContain('doc.pdf')
  })

  it('shows empty state for no files', () => {
    const wrapper = mount(FileCard, {
      props: { files: [] },
    })

    expect(wrapper.find('.file-card').exists()).toBe(true)
  })
})
