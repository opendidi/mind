import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import AgentInput from '@/components/AgentPanel/AgentInput.vue'

describe('AgentInput.vue', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('renders textarea and send button', () => {
    const wrapper = mount(AgentInput, {
      props: { disabled: false },
      global: { stubs: { teleport: true } },
    })

    expect(wrapper.find('textarea').exists()).toBe(true)
    expect(wrapper.find('.send-btn').exists()).toBe(true)
  })

  it('sends message on button click', async () => {
    const wrapper = mount(AgentInput, {
      props: { disabled: false },
    })

    await wrapper.find('textarea').setValue('Hello World')
    await wrapper.find('.send-btn').trigger('click')

    const emits = wrapper.emitted('send')
    expect(emits).toBeTruthy()
    expect(emits![0]).toEqual(['Hello World', []])
  })

  it('disables send button when input empty and no images', () => {
    const wrapper = mount(AgentInput, {
      props: { disabled: false },
    })

    const btn = wrapper.find('.send-btn')
    expect(btn.attributes('disabled')).toBeDefined()
  })

  it('inserts text when presetContext changes', async () => {
    const wrapper = mount(AgentInput, {
      props: { disabled: false, presetContext: '引用内容' },
    })

    const textarea = wrapper.find('textarea') as any
    expect(textarea.element.value).toContain('引用内容')
  })
})
