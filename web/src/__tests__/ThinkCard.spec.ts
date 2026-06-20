import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import ThinkCard from '@/components/chat/ThinkCard.vue'

describe('ThinkCard.vue', () => {
  it('renders thinking content', () => {
    const wrapper = mount(ThinkCard, {
      props: {
        content: '正在分析用户意图...',
        thinking: true,
      },
    })

    expect(wrapper.text()).toContain('正在分析用户意图...')
  })

  it('is open by default when thinking is true', () => {
    const wrapper = mount(ThinkCard, {
      props: {
        content: '分析完毕',
        thinking: true,
      },
    })

    // Should show the content when open
    expect(wrapper.find('.thinking-body').exists()).toBe(true)
  })

  it('is collapsed when thinking is false', () => {
    const wrapper = mount(ThinkCard, {
      props: {
        content: '分析完毕',
        thinking: false,
      },
    })

    // The summary label should be visible
    expect(wrapper.text()).toContain('思考过程')
  })
})
