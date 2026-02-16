import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { defineComponent, ref } from 'vue'

import { useFilterPopouts } from '../useFilterPopouts'

describe('useFilterPopouts', () => {
  it('does not trigger Vue warning when product filter source is used', () => {
    const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {})
    const TestComponent = defineComponent({
      setup() {
        useFilterPopouts({
          activeDealFilter: ref(''),
          activeProductFilter: ref(''),
          activeAccountFilter: ref(''),
        })
        return {}
      },
      template: '<div />',
    })

    mount(TestComponent)
    expect(warnSpy).not.toHaveBeenCalled()
    warnSpy.mockRestore()
  })

  it('does not trigger Vue warning when product/game filter is omitted', () => {
    const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {})
    const TestComponent = defineComponent({
      setup() {
        useFilterPopouts({
          activeDealFilter: ref(''),
          activeAccountFilter: ref(''),
        })
        return {}
      },
      template: '<div />',
    })

    mount(TestComponent)
    expect(warnSpy).not.toHaveBeenCalled()
    warnSpy.mockRestore()
  })
})
