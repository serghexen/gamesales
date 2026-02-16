import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { reactive, ref } from 'vue'

import WorkProductEditorModal from '../sections/WorkProductEditorModal.vue'

function buildCtx(overrides = {}) {
  // Собираем минимальный контекст модалки, чтобы проверить заголовок в edit/create сценариях.
  return {
    editProduct: reactive({
      open: true,
      product_id: 1,
      type_code: 'game',
      title: 'EA FC 26',
      short_title: '',
      link: '',
      text_lang: '',
      audio_lang: '',
      vr_support: '',
      platform_codes: [],
      region_code: '',
      provider: '',
      billing_period: '',
      subscription_notes: '',
    }),
    showProductForm: false,
    closeProductModal: () => {},
    modalRef: ref(null),
    modalStyle: {},
    startModalDrag: () => {},
    productEditMode: 'view',
    updateProduct: () => {},
    productLoading: false,
    createProduct: () => {},
    archiveProduct: () => {},
    platforms: [],
    getRegionLabel: () => '—',
    regions: [],
    productAccountsError: null,
    productAccountsLoading: false,
    productAccounts: [],
    productAccountsSort: { key: 'free_slots', dir: 'desc' },
    pagedProductAccounts: [],
    sortProductAccounts: () => {},
    openAccountFromProduct: () => {},
    productAccountsTotalPages: 1,
    productAccountsPage: 1,
    prevProductAccountsPage: () => {},
    nextProductAccountsPage: () => {},
    productSlotAssignmentsError: null,
    productSlotAssignmentsLoading: false,
    productSlotAssignments: [],
    getSlotTypeLabel: () => '—',
    getSlotAssignmentStatus: () => '—',
    formatDateTimeMinutes: () => '—',
    productError: null,
    productOk: null,
    newProduct: reactive({
      type_code: 'game',
      title: '',
      short_title: '',
      link: '',
      text_lang: '',
      audio_lang: '',
      vr_support: '',
      platform_codes: [],
      region_code: '',
      provider: '',
      billing_period: '',
      subscription_notes: '',
    }),
    ...overrides,
  }
}

describe('WorkProductEditorModal', () => {
  it('shows edit header for game product', () => {
    const wrapper = mount(WorkProductEditorModal, {
      props: { ctx: buildCtx() },
      global: {
        stubs: {
          teleport: true,
        },
      },
    })

    expect(wrapper.find('h3').text()).toBe('ТОВАР (ИГРА) - EA FC 26')
  })

  it('shows edit header for subscription product', () => {
    const wrapper = mount(WorkProductEditorModal, {
      props: {
        ctx: buildCtx({
          editProduct: reactive({
            open: true,
            product_id: 2,
            type_code: 'subscription',
            title: 'PS Plus',
            short_title: '',
            link: '',
            text_lang: '',
            audio_lang: '',
            vr_support: '',
            platform_codes: [],
            region_code: '',
            provider: '',
            billing_period: '',
            subscription_notes: '',
          }),
        }),
      },
      global: {
        stubs: {
          teleport: true,
        },
      },
    })

    expect(wrapper.find('h3').text()).toBe('ТОВАР (ПОДПИСКА) - PS Plus')
  })

  it('sorts slots table by selected column', async () => {
    const wrapper = mount(WorkProductEditorModal, {
      props: {
        ctx: buildCtx({
          productSlotAssignments: [
            { assignment_id: 2, account_login: 'z-user@mail.com', slot_type_code: 'ps5', customer_nickname: '', assigned_at: '2026-01-01T10:00:00Z', released_at: null },
            { assignment_id: 1, account_login: 'a-user@mail.com', slot_type_code: 'ps4', customer_nickname: '', assigned_at: '2026-01-01T10:00:00Z', released_at: null },
          ],
          getSlotTypeLabel: (code) => code,
          getSlotAssignmentStatus: () => 'active',
        }),
      },
      global: {
        stubs: {
          teleport: true,
        },
      },
    })

    const slotToggle = wrapper.findAll('.section-toggle')[1]
    await slotToggle.trigger('click')

    const accountSortBtn = wrapper.find('[aria-label="Сортировка слотов по аккаунту"]')
    await accountSortBtn.trigger('click')

    const firstRowText = wrapper.find('tbody tr').text()
    expect(firstRowText).toContain('a-user@mail.com')
  })

  it('opens account by click on account cell and ignores click when text is selected', async () => {
    const openAccountFromProduct = vi.fn()
    const wrapper = mount(WorkProductEditorModal, {
      props: {
        ctx: buildCtx({
          productAccounts: [
            { account_id: 1, login_full: 'acc@test.com', platform_code: 'ps5', free_slots: 1, occupied_slots: 1 },
          ],
          pagedProductAccounts: [
            { account_id: 1, login_full: 'acc@test.com', platform_code: 'ps5', free_slots: 1, occupied_slots: 1 },
          ],
          productAccountsTotalPages: 1,
          openAccountFromProduct,
        }),
      },
      global: {
        stubs: {
          teleport: true,
        },
      },
    })

    const accountToggle = wrapper.findAll('.section-toggle')[0]
    await accountToggle.trigger('click')

    const getSelectionSpy = vi.spyOn(window, 'getSelection')
    getSelectionSpy.mockImplementation(() => ({ toString: () => '' }))
    await wrapper.find('tbody tr td').trigger('click')
    expect(openAccountFromProduct).toHaveBeenCalledWith('acc@test.com')

    getSelectionSpy.mockImplementation(() => ({ toString: () => 'acc@test.com' }))
    await wrapper.find('tbody tr td').trigger('click')
    expect(openAccountFromProduct).toHaveBeenCalledTimes(1)

    getSelectionSpy.mockRestore()
  })
})
