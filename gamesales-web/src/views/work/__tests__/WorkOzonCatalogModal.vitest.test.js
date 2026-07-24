import { describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'

import WorkOzonCatalogModal from '../sections/WorkOzonCatalogModal.vue'

function buildProps() {
  // Передает активную и архивную карточки, чтобы проверить раздельный список без обращения к Ozon.
  return {
    showOzonCatalog: true,
    closeOzonCatalog: vi.fn(),
    syncOzonCatalog: vi.fn(),
    updateOzonCatalogArchive: vi.fn(),
    openOzonCatalogDetails: vi.fn(),
    ozonCatalogItems: [
      { external_product_id: 101, offer_id: 'active-100', sku: '5510101', title: 'Активный товар', visibility: 'VISIBLE', synced_at: '2026-07-24T08:30:00Z' },
      { external_product_id: 102, offer_id: 'archive-100', sku: '5510102', title: 'Архивный товар', visibility: 'ARCHIVED', synced_at: '2026-07-24T08:30:00Z' },
    ],
    ozonCatalogLoading: false,
    ozonCatalogSyncing: false,
    ozonCatalogItemActionId: 0,
  }
}

describe('WorkOzonCatalogModal', () => {
  it('shows the hamster while the catalog is loading or synchronizing', () => {
    const props = buildProps()
    props.ozonCatalogSyncing = true
    const wrapper = mount(WorkOzonCatalogModal, {
      props,
      global: { stubs: { teleport: true } },
    })

    expect(wrapper.find('.modal__body-overlay .wheel-and-hamster').exists()).toBe(true)
    expect(wrapper.text()).toContain('Синхронизируем каталог Ozon…')
    expect(wrapper.get('.modal__body').classes()).toContain('modal__body--loader')
    expect(wrapper.text()).not.toContain('Снимка каталога пока нет.')
  })

  it('separates archived Ozon cards from active cards', async () => {
    const wrapper = mount(WorkOzonCatalogModal, {
      props: buildProps(),
      global: { stubs: { teleport: true } },
    })

    expect(wrapper.text()).toContain('Активный товар')
    expect(wrapper.text()).toContain('SKU: 5510101')
    expect(wrapper.text()).not.toContain('Архивный товар')
    expect(wrapper.text()).toContain('Последняя синхронизация')
    expect(wrapper.findAll('.ozon-catalog-modal__close-btn')).toHaveLength(1)
    expect(wrapper.findAll('.ozon-catalog-modal__sync-btn.deal-create-action-btn--refresh')).toHaveLength(1)

    const tabs = wrapper.findAll('.ozon-catalog-modal__tab')
    await tabs[1].trigger('click')

    expect(wrapper.text()).toContain('Архивный товар')
    expect(wrapper.text()).not.toContain('Активный товар')
    expect(wrapper.text()).toContain('Восстановить')

    await wrapper.get('input[type="search"]').setValue('5510102')

    expect(wrapper.text()).toContain('Архивный товар')
    expect(wrapper.text()).not.toContain('Активный товар')
  })
})
