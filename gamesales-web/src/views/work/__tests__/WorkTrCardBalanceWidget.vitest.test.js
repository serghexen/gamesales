import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import WorkTrCardBalanceWidget from '../sections/WorkTrCardBalanceWidget.vue'

function buildCtx(overrides = {}) {
  // Проверяем сохранённый функционал отдельно от шапки, где виджет временно отключён.
  return {
    canManageRolePermissions: true,
    financeTrCardBalance: { current_balance: 19000 },
    financeTrCardBalanceDraft: '19000',
    financeTrCardBalanceLoading: false,
    financeTrCardBalanceSaving: false,
    financeTrCardBalanceError: '',
    loadFinanceTrCardBalance: vi.fn(),
    saveFinanceTrCardBalance: vi.fn().mockResolvedValue(true),
    formatPrice: (value) => String(Math.round(Number(value || 0))),
    ...overrides,
  }
}

function mountWidget(ctx) {
  // Редактор рендерится внутри теста, не открывая реальный интерфейс приложения.
  return mount(WorkTrCardBalanceWidget, { props: { ctx }, global: { stubs: { teleport: true } } })
}

describe('WorkTrCardBalanceWidget — preserved while hidden', () => {
  it('shows the balance without editing controls for an ordinary user', () => {
    // Временное скрытие не меняет существующие ограничения редактора.
    const wrapper = mountWidget(buildCtx({ canManageRolePermissions: false }))
    expect(wrapper.find('[data-test="finance-tr-card-balance"]').text()).toContain('19000 TRY')
    expect(wrapper.find('[data-test="finance-edit-tr-card-balance"]').exists()).toBe(false)
    wrapper.unmount()
  })

  it('allows privileged users to refresh and edit TR card balance', async () => {
    // Сохраняем прежнее покрытие обновления и ручной корректировки баланса.
    const ctx = buildCtx({ financeTrCardBalance: { current_balance: -500 } })
    const wrapper = mountWidget(ctx)
    expect(wrapper.find('.tr-card-balance__value').classes()).toContain('tr-card-balance__value--negative')
    await wrapper.find('[data-test="finance-refresh-tr-card-balance"]').trigger('click')
    expect(ctx.loadFinanceTrCardBalance).toHaveBeenCalledTimes(1)
    await wrapper.find('[data-test="finance-edit-tr-card-balance"]').trigger('click')
    expect(wrapper.find('[aria-label="Фактический баланс TR-карты"]').exists()).toBe(true)
    await wrapper.find('[data-test="finance-save-tr-card-balance"]').trigger('click')
    expect(ctx.saveFinanceTrCardBalance).toHaveBeenCalledTimes(1)
    wrapper.unmount()
  })

  it('shows loader while TR balance is refreshing', () => {
    // Индикатор загрузки остаётся рабочим для будущего возврата виджета.
    const wrapper = mountWidget(buildCtx({ financeTrCardBalanceLoading: true }))
    expect(wrapper.find('[data-test="finance-refresh-tr-card-balance"] .wheel-and-hamster').exists()).toBe(true)
    wrapper.unmount()
  })
})
