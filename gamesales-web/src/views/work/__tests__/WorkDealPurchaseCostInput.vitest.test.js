import { describe, it, expect, vi } from 'vitest'
import { reactive } from 'vue'
import { mount } from '@vue/test-utils'
import WorkDealPurchaseCostInput from '../sections/WorkDealPurchaseCostInput.vue'

describe('WorkDealPurchaseCostInput', () => {
  it.each(['TR', 'PL'])('shows saved %s cost without allowing edits in either form mode', async (region) => {
    // Старый закуп виден и в просмотре, и в редактировании, но событие ввода не меняет сумму.
    const deal = reactive({ deal_id: 42, deal_type_code: 'sale', region_code: region, purchase_cost: 475.04 })
    const clampPrice = vi.fn(Number)
    const wrapper = mount(WorkDealPurchaseCostInput, { props: { deal, max: 100000, clampPrice } })
    const input = wrapper.get('input')
    expect(input.element.value).toBe('475.04')
    expect(input.element.disabled).toBe(true)
    input.element.value = '123'
    input.element.dispatchEvent(new Event('input'))
    expect(clampPrice).not.toHaveBeenCalled()
    expect(deal.purchase_cost).toBe(475.04)
    await wrapper.setProps({ readonly: true })
    expect(input.element.disabled).toBe(true)
    wrapper.unmount()
  })

  it.each(['TR', 'PL'])('keeps new %s cost empty and disabled until the deal is saved', async (region) => {
    // Новая карточка не предлагает ручной ввод; после сохранения показывает учётную сумму.
    const deal = reactive({ deal_type_code: 'sale', region_code: region, purchase_cost: 0 })
    const wrapper = mount(WorkDealPurchaseCostInput, { props: { deal, max: 100000, clampPrice: Number } })
    expect(wrapper.get('input').element.value).toBe('')
    expect(wrapper.get('input').element.disabled).toBe(true)
    await wrapper.setProps({ deal: { ...deal, deal_id: 42, purchase_cost: 950.08 } })
    expect(wrapper.get('input').element.value).toBe('950.08')
    expect(wrapper.get('input').element.disabled).toBe(true)
    wrapper.unmount()
  })

  it('keeps decimal input for other regions and respects view mode', async () => {
    // Обычные услуги сохраняют прежний ввод дробной закупочной цены.
    const deal = reactive({ deal_type_code: 'sale', region_code: 'US', purchase_cost: 50 })
    const wrapper = mount(WorkDealPurchaseCostInput, { props: { deal, max: 100000, clampPrice: Number } })
    const input = wrapper.get('input')
    expect(input.element.disabled).toBe(false)
    expect(input.attributes('step')).toBe('0.01')
    await input.setValue('123.45')
    expect(deal.purchase_cost).toBe(123.45)
    await wrapper.setProps({ readonly: true })
    await input.setValue('999')
    expect(deal.purchase_cost).toBe(123.45)
    wrapper.unmount()
  })
})
