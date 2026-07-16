import { describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'

import WorkInterhubSection from '../sections/WorkInterhubSection.vue'

function buildCtx(overrides = {}) {
  // Собираем каталог как его отдаёт внутренний endpoint InterHub.
  return {
    loading: false,
    error: '',
    search: '',
    services: [
      {
        service_id: 7,
        title: 'Mobile top up',
        category: 'Mobile',
        type: 'TOP_UP_FIXED',
        min_amount: 10,
        max_amount: 100,
        fields: [{ name: 'nominal', required: true }],
      },
      {
        service_id: 8,
        title: 'Gift PIN',
        category: 'Games',
        type: 'PIN',
        min_amount: 0,
        max_amount: 0,
        fields: [],
      },
    ],
    reload: vi.fn(),
    setSearchFromEvent: vi.fn(),
    ...overrides,
  }
}

describe('WorkInterhubSection', () => {
  it('renders normalized services and payment types', () => {
    const wrapper = mount(WorkInterhubSection, { props: { ctx: buildCtx() } })

    expect(wrapper.text()).toContain('Mobile top up')
    expect(wrapper.text()).toContain('Фикс. номинал')
    expect(wrapper.text()).toContain('PIN-код')
    expect(wrapper.text()).toContain('nominal')
  })

  it('filters catalog locally and reloads on demand', async () => {
    const ctx = buildCtx()
    const wrapper = mount(WorkInterhubSection, { props: { ctx } })

    await wrapper.find('input[type="search"]').setValue('games')
    expect(ctx.setSearchFromEvent).toHaveBeenCalledTimes(1)

    await wrapper.setProps({ ctx: { ...ctx, search: 'games' } })
    expect(wrapper.text()).not.toContain('Mobile top up')
    expect(wrapper.text()).toContain('Gift PIN')

    await wrapper.find('[aria-label="Обновить каталог InterHub"]').trigger('click')
    expect(ctx.reload).toHaveBeenCalledTimes(1)
  })
})
