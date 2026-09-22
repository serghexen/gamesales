import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import WorkVoucherCatalogNominal from '../sections/WorkVoucherCatalogNominal.vue'

const now = Date.parse('2026-09-20T07:30:00Z')
function offer(id, priority, enabled = true, overrides = {}) {
  // Разные цены и нулевой остаток проверяют, что сводка следует приоритету, а не выгодности предложения.
  return { offer_id: id, supplier_code: `supplier-${id}`, supplier_name: `Поставщик ${id}`,
    service_title: 'Blizzard — EUR', nominal_title: 'EUR 20', fulfillment_priority: priority,
    fulfillment_enabled: enabled, price: 2000 + id, currency: 'RUB', stock_count: id,
    price_updated_at: '2026-09-20T06:00:00Z', stock_updated_at: '2026-09-20T07:00:00Z',
    price_error: '', stock_error: '', ...overrides }
}
function setup(overrides = {}) {
  // Приоритеты намеренно перемешаны во входных данных, чтобы проверить обе видимые последовательности.
  return mount(WorkVoucherCatalogNominal, { props: { canEdit: true, now,
    nominal: { catalog_nominal_id: 11, name: 'EUR 20', sku: 'HT0000001', offers: [offer(3, 3, true, { price: 100 }), offer(1, 1, false), offer(2, 2, true, { stock_count: 0 })] }, ...overrides } })
}

describe('WorkVoucherCatalogNominal', () => {
  it('starts collapsed and summarizes the first enabled supplier regardless of cheaper price or zero stock', async () => {
    const wrapper = setup()
    expect(wrapper.find('.catalog-nominal__expand').attributes('aria-expanded')).toBe('false')
    expect(wrapper.find('.catalog-nominal__details').exists()).toBe(false)
    expect(wrapper.find('.catalog-nominal__first').text()).toContain('Поставщик 2')
    expect(wrapper.find('.catalog-nominal__count').text()).toBe('3 поставщика')
    expect(wrapper.find('.catalog-nominal__sku').text()).toBe('HT0000001')
    expect(wrapper.findAll('.voucher-catalog__number').map((node) => node.text())).toEqual(['2 002,00 ₽', '0'])
    expect(wrapper.find('.catalog-nominal__summary').text()).toContain('Нет в наличии')
    await wrapper.find('.catalog-nominal__expand').trigger('click')
    expect(wrapper.emitted('edit')).toBeUndefined()
    expect(wrapper.findAll('.catalog-nominal__offer').map((row) => row.attributes('data-offer-id'))).toEqual(['1', '2', '3'])
    expect(wrapper.findAll('.catalog-nominal__offer')[0].classes()).toContain('is-disabled')
    expect(wrapper.find('.catalog-nominal__details').text()).toContain('09:00')
    await wrapper.find('.voucher-catalog__nominal').trigger('click')
    expect(wrapper.emitted('edit')).toHaveLength(1)
    expect(wrapper.find('.catalog-nominal__expand').attributes('aria-expanded')).toBe('true')
  })

  it('does not show a disabled supplier as the summary when all suppliers are off', async () => {
    const wrapper = setup({ nominal: { catalog_nominal_id: 11, name: 'EUR 20', offers: [offer(1, 1, false)] } })
    expect(wrapper.find('.catalog-nominal__first').text()).toContain('Автовыдача отключена')
    expect(wrapper.findAll('.voucher-catalog__number').map((node) => node.text())).toEqual(['—', '—'])
    await wrapper.find('.catalog-nominal__expand').trigger('click')
    expect(wrapper.find('.catalog-nominal__details').text()).toContain('2 001,00 ₽')
  })

  it('keeps expansion on snapshot refresh and reveals search matches without locking the collapse control', async () => {
    const wrapper = setup()
    await wrapper.setProps({ search: 'Поставщик 3' })
    expect(wrapper.find('.catalog-nominal__details').exists()).toBe(true)
    await wrapper.setProps({ nominal: { catalog_nominal_id: 11, name: 'EUR 20', offers: [offer(2, 1, true, { price: 0, stock_count: null, stock_error: 'Нет ответа', stock_checked_at: '2026-09-20T07:00:00Z' })] } })
    expect(wrapper.find('.catalog-nominal__details').exists()).toBe(true)
    expect(wrapper.find('.catalog-nominal__summary').text()).toContain('0,00 ₽')
    expect(wrapper.find('.catalog-nominal__summary').text()).toContain('Нет ответа')
    expect(wrapper.find('.catalog-nominal__summary').text()).not.toContain('Нет в наличии')
    expect(wrapper.find('.catalog-snapshot__problem').attributes('title')).toContain('10:00')
    await wrapper.find('.catalog-nominal__expand').trigger('click')
    expect(wrapper.find('.catalog-nominal__details').exists()).toBe(false)
  })

  it('requires confirmation for unlink and keeps deleting a nominal a separate event', async () => {
    const wrapper = setup()
    await wrapper.find('.catalog-nominal__expand').trigger('click')
    const row = wrapper.find('[data-offer-id="2"]')
    await row.find('button').trigger('click')
    expect(wrapper.emitted('unlink')).toBeUndefined()
    await row.findAll('button').find((button) => button.text() === 'Отмена').trigger('click')
    expect(row.text()).not.toContain('Убрать связку?')
    await row.find('button').trigger('click')
    await row.findAll('button').find((button) => button.text() === 'Да').trigger('click')
    expect(wrapper.emitted('unlink')).toEqual([[2]])
    await wrapper.find('.voucher-catalog__delete-nominal').trigger('click')
    expect(wrapper.emitted('delete')).toHaveLength(1)
  })

  it('shows unlinked nominals and readonly supplier details without edit actions', async () => {
    const empty = setup({ nominal: { catalog_nominal_id: 11, name: '150', offers: [] } })
    expect(empty.find('.catalog-nominal__expand').element.disabled).toBe(true)
    expect(empty.text()).toContain('0 поставщиков')
    await empty.find('.catalog-nominal__action').trigger('click')
    expect(empty.emitted('edit')).toHaveLength(1)
    const reader = setup({ canEdit: false })
    await reader.find('.catalog-nominal__expand').trigger('click')
    expect(reader.find('.catalog-nominal__details').exists()).toBe(true)
    expect(reader.find('.voucher-catalog__nominal').exists()).toBe(false)
    expect(reader.find('.voucher-catalog__delete-nominal').exists()).toBe(false)
    expect(reader.text()).not.toContain('Отвязать')
    expect(reader.text()).not.toContain('Настроить поставщиков')
  })

  it('counts distinct suppliers and shows stale snapshots in both compact and detailed views', async () => {
    const wrapper = setup({ nominal: { catalog_nominal_id: 11, name: 'EUR 20', offers: [
      offer(1, 1, true, { price_updated_at: '2026-09-18T06:00:00Z', stock_updated_at: '2026-09-18T06:00:00Z' }),
      offer(2, 2, true, { supplier_code: 'supplier-1' }),
    ] } })
    expect(wrapper.find('.catalog-nominal__count').text()).toBe('1 поставщик')
    expect(wrapper.find('.catalog-nominal__summary').text()).toContain('Цена требует обновления')
    expect(wrapper.find('.catalog-nominal__summary').text()).toContain('Остаток требует обновления')
    await wrapper.find('.catalog-nominal__expand').trigger('click')
    expect(wrapper.find('.catalog-nominal__details').text()).toContain('Цена требует обновления')
  })
})
