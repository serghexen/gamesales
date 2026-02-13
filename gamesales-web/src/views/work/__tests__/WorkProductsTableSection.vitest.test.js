import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'

import WorkProductsTableSection from '../sections/WorkProductsTableSection.vue'

function buildProps(overrides = {}) {
  // Собираем базовые пропсы таблицы, чтобы в тестах переопределять только нужное.
  return {
    sortedProducts: [],
    pagedProducts: [],
    productFilters: {
      q: '',
      type_code: '',
      platform_code: '',
      region_code: '',
    },
    activeProductFilter: '',
    productFilterDraft: {
      title: '',
      type: '',
      platform: '',
      region: '',
    },
    openProductFilter: () => {},
    toggleProductsSort: () => {},
    getProductsSortClass: () => '',
    applyProductFilter: () => {},
    resetProductFilter: () => {},
    formatProductPlatforms: (platforms) => (platforms || []).join(', '),
    openProductAccounts: () => {},
    ...overrides,
  }
}

describe('WorkProductsTableSection', () => {
  it('shows columns in order type, title, platform with expected widths', () => {
    localStorage.clear()
    const wrapper = mount(WorkProductsTableSection, {
      props: buildProps({
        sortedProducts: [{ product_id: 1 }],
        pagedProducts: [
          {
            product_id: 1,
            title: 'EA FC 26',
            type_code: 'game',
            short_title: 'FC26',
            platform_codes: ['ps5'],
            region_code: 'RU',
          },
        ],
      }),
    })

    const headers = wrapper.findAll('thead th').map((th) => th.text().trim())
    expect(headers).not.toContain('Короткое')
    expect(headers).not.toContain('Регион')
    expect(headers[0]).toContain('Тип')
    expect(headers[1]).toContain('Товар')
    expect(headers[2]).toContain('Платформа')

    const headerClasses = wrapper.findAll('thead th').map((th) => th.attributes('class') || '')
    expect(headerClasses[0]).toContain('product-col-type')
    expect(headerClasses[1]).toContain('product-col-title')
    expect(headerClasses[2]).toContain('product-col-platform')

    const colWidths = wrapper.findAll('col').map((col) => col.attributes('style') || '')
    expect(colWidths[0]).toContain('18%')
    expect(colWidths[1]).toContain('62%')
    expect(colWidths[2]).toContain('20%')

    const resizers = wrapper.findAll('.table-col-resizer')
    expect(resizers).toHaveLength(2)

    const cells = wrapper.findAll('tbody tr td').map((td) => td.text().trim())
    expect(cells).toEqual(['Игра', 'EA FC 26', 'ps5'])
    expect(wrapper.text()).not.toContain('FC26')
    expect(wrapper.text()).not.toContain('RU')
  })

  it('loads saved column widths from localStorage', async () => {
    localStorage.setItem('work.products.columns.v1', JSON.stringify({ type: 25, title: 55, platform: 20 }))
    const wrapper = mount(WorkProductsTableSection, {
      props: buildProps({
        sortedProducts: [{ product_id: 1 }],
        pagedProducts: [{ product_id: 1, title: 'EA FC 26', type_code: 'game', platform_codes: ['ps5'] }],
      }),
    })
    await nextTick()

    const colWidths = wrapper.findAll('col').map((col) => col.attributes('style') || '')
    expect(colWidths[0]).toContain('25%')
    expect(colWidths[1]).toContain('55')
    expect(colWidths[2]).toContain('20%')
  })
})
