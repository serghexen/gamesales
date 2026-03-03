import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'

import WorkNsGiftSection from '../sections/WorkNsGiftSection.vue'

function buildCtx(overrides = {}) {
  // Готовим минимальный контекст для проверки баланса и выбора категории.
  return {
    loading: false,
    error: '',
    ok: '',
    balance: 50.0458,
    categories: [
      { category_id: 2, name: 'Steam' },
      { category_id: 3, name: 'PSN' },
      { category_id: 4, name: 'Netflix' },
    ],
    selectedCategory: 'Steam',
    selectedCategoryId: 2,
    services: [
      { service_id: 101, title: 'Steam Gift Card 10', category: 'Steam', price: 9.99, currency: 'USD', min_quantity: 1, max_quantity: 10 },
      { service_id: 102, title: 'Steam Gift Card 20', category: 'Steam', price: 19.99, currency: 'USD', min_quantity: 1, max_quantity: 10 },
    ],
    servicesLoading: false,
    servicesSearch: '',
    steamMode: false,
    steamLogin: '',
    steamAmount: '1',
    steamCurrencyRate: { date: '2026-03-02', rubUsd: 76.93, kztUsd: 500.41, uahUsd: 43.23 },
    steamLoading: false,
    reloadNsGiftData: vi.fn(),
    toggleSteamMode: vi.fn(),
    setSelectedCategoryFromEvent: vi.fn(),
    selectCategoryText: vi.fn(),
    selectCategoryOption: vi.fn(),
    setServicesSearchFromEvent: vi.fn(),
    setSteamLoginFromEvent: vi.fn(),
    setSteamAmountFromEvent: vi.fn(),
    ...overrides,
  }
}

describe('WorkNsGiftSection', () => {
  it('renders balance and categories input', () => {
    const ctx = buildCtx()
    const wrapper = mount(WorkNsGiftSection, {
      props: { ctx },
    })

    expect(wrapper.text()).toContain('NS Gift')
    expect(wrapper.text()).toContain('Баланс')
    expect(wrapper.text()).toContain('USD')
    expect(wrapper.text()).toContain('Всего: 3')
    expect(wrapper.text()).toContain('PlayStation')
    expect(wrapper.find('.work-ns-gift__input').exists()).toBe(true)
    expect(wrapper.text()).toContain('Steam Gift Card 10')
  })

  it('triggers reload and category input handlers', async () => {
    const ctx = buildCtx()
    const wrapper = mount(WorkNsGiftSection, {
      props: { ctx },
    })

    await wrapper.find('button').trigger('click')
    expect(ctx.reloadNsGiftData).toHaveBeenCalledTimes(1)

    const input = wrapper.find('.work-ns-gift__input')
    await input.setValue('PSN')
    expect(ctx.setSelectedCategoryFromEvent).toHaveBeenCalledTimes(1)

    const quickCards = wrapper.findAll('.work-ns-gift__quick-card')
    await quickCards[0].trigger('click')
    expect(ctx.selectCategoryText).toHaveBeenCalledWith('Steam')
    expect(ctx.toggleSteamMode).toHaveBeenCalledTimes(0)
  })

  it('sorts services by title when sort button is clicked', async () => {
    const ctx = buildCtx({
      services: [
        { service_id: 102, title: 'Zulu card', price: 19.99, currency: 'USD', in_stock: 3 },
        { service_id: 101, title: 'Alpha card', price: 9.99, currency: 'USD', in_stock: 8 },
      ],
    })
    const wrapper = mount(WorkNsGiftSection, { props: { ctx } })

    const rowsBefore = wrapper.findAll('tbody tr')
    expect(rowsBefore[0].text()).toContain('Alpha card')

    await wrapper.find('[aria-label="Сортировка по наименованию"]').trigger('click')
    const rowsAfter = wrapper.findAll('tbody tr')
    expect(rowsAfter[0].text()).toContain('Zulu card')
  })

  it('shows closest category matches first in dropdown', async () => {
    const ctx = buildCtx({
      categories: [
        { category_id: 1, name: 'Steam Wallet' },
        { category_id: 2, name: 'EA' },
        { category_id: 3, name: 'PlayStation EA Pack' },
      ],
      selectedCategory: 'EA',
    })
    const wrapper = mount(WorkNsGiftSection, { props: { ctx } })

    const input = wrapper.find('.work-ns-gift__input')
    await input.trigger('focus')

    const options = wrapper.findAll('.work-ns-gift__dropdown-item')
    expect(options.length).toBeGreaterThan(0)
    expect(options[0].text()).toBe('EA')
  })

  it('calculates final price based on selected quantity', async () => {
    const ctx = buildCtx({
      services: [
        { service_id: 301, title: 'EA FC Points', price: 5.646, currency: 'USD', in_stock: 5 },
      ],
    })
    const wrapper = mount(WorkNsGiftSection, { props: { ctx } })

    expect(wrapper.text()).toContain('купить')

    const increaseButtons = wrapper.findAll('[aria-label="Увеличить количество"]')
    await increaseButtons[0].trigger('click')
    expect(wrapper.text()).toContain('5.65 USD')
  })

  it('renders steam form for category 68', async () => {
    const ctx = buildCtx({
      steamMode: true,
      selectedCategoryId: 68,
      services: [],
    })
    const wrapper = mount(WorkNsGiftSection, { props: { ctx } })
    expect(wrapper.text()).toContain('Steam Login')
    expect(wrapper.text()).toContain('Валюта')
    expect(wrapper.text()).toContain('RUB')
    expect(wrapper.text()).toContain('76.93')

    const steamLoginInput = wrapper.find('.work-ns-gift__card--steam-form input[type="text"]')
    await steamLoginInput.setValue('my-login')
    expect(ctx.setSteamLoginFromEvent).toHaveBeenCalledTimes(1)
  })

  it('toggles steam form by steam tile click', async () => {
    const ctx = buildCtx()
    const wrapper = mount(WorkNsGiftSection, { props: { ctx } })
    await wrapper.find('.work-ns-gift__steam-tile').trigger('click')
    expect(ctx.toggleSteamMode).toHaveBeenCalledTimes(1)
  })
})
