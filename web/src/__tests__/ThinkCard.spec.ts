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

  it('shows thinking label when thinking is true', () => {
    const wrapper = mount(ThinkCard, {
      props: {
        content: '分析完毕',
        thinking: true,
      },
    })

    // Shows "深度思考中" when still thinking
    expect(wrapper.text()).toContain('深度思考中')
  })

  it('shows done label when thinking is false', () => {
    const wrapper = mount(ThinkCard, {
      props: {
        content: '分析完毕',
        thinking: false,
      },
    })

    // Shows completion summary when thinking is done
    expect(wrapper.text()).toContain('已深度思考分析完毕')
  })
})
