import { afterEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import WorkVoucherSelect from '../sections/WorkVoucherSelect.vue'

const wrappers = []
function setup(rect = { left: 100, top: 100, bottom: 136, width: 160 }) {
  // Размер поля задаём явно, чтобы проверить направление меню без системного select.
  const wrapper = mount(WorkVoucherSelect, { attachTo: document.body, props: {
    modelValue: 'interhub', options: [{ code: 'interhub', name: 'Интерхаб' }, { code: 'warehouse', name: 'Склад' }],
  } })
  wrappers.push(wrapper)
  vi.spyOn(wrapper.get('button').element, 'getBoundingClientRect').mockReturnValue(rect)
  return wrapper
}
afterEach(() => {
  // Телепорт и обработчики не должны оставаться после закрытия карточки.
  wrappers.splice(0).forEach((wrapper) => wrapper.unmount())
  vi.restoreAllMocks()
  document.body.innerHTML = ''
})

describe('Меню каталога', () => {
  it('keeps linked suppliers visible but skips disabled options by mouse and keyboard', async () => {
    // Уже связанный склад нельзя добавить ни кликом, ни клавиатурой.
    const wrapper = setup()
    await wrapper.setProps({ options: [
      { code: 'warehouse', name: 'Склад · уже связан', disabled: true },
      { code: 'interhub', name: 'Интерхаб' },
      { code: 'third', name: 'Третий', disabled: true },
      { code: 'other', name: 'Другой' },
    ] })
    const field = wrapper.get('button')
    await field.trigger('click')
    const unavailable = document.querySelector('[role="option"][aria-disabled="true"]')
    unavailable.click()
    await wrapper.vm.$nextTick()
    expect(wrapper.emitted('change')).toBeUndefined()
    expect(field.attributes('aria-expanded')).toBe('true')
    await field.trigger('keydown', { key: 'Home' })
    expect(field.attributes('aria-activedescendant')).toMatch(/-1$/)
    await field.trigger('keydown', { key: 'ArrowDown' })
    expect(field.attributes('aria-activedescendant')).toMatch(/-3$/)
    await field.trigger('keydown', { key: 'Enter' })
    expect(wrapper.emitted('update:modelValue')).toEqual([['other']])
    await wrapper.setProps({ options: [{ code: 'warehouse', name: 'Склад', disabled: true }] })
    expect(field.element.disabled).toBe(true)
  })

  it('copies field typography into the teleported list', async () => {
    // Перенос в body не должен подменять шрифт интерфейса системным serif.
    const wrapper = setup()
    wrapper.get('button').element.style.fontFamily = '"Space Grotesk", sans-serif'
    wrapper.get('button').element.style.fontSize = '13px'
    wrapper.get('button').element.style.fontWeight = '400'
    const font = getComputedStyle(wrapper.get('button').element)
    await wrapper.get('button').trigger('click')
    const menu = document.querySelector('[role="listbox"]')
    expect(menu.style.fontFamily).toBe(font.fontFamily)
    expect(menu.style.fontSize).toBe('13px')
    expect(menu.style.fontWeight).toBe('400')
  })

  it('handles a long service list and can reset the selected service', async () => {
    // Одинаковый компонент подходит услугам: длинный список ограничен по высоте, пустой выбор сохраняется.
    const wrapper = setup()
    await wrapper.setProps({ label: 'Услуга поставщика', modelValue: '80', options: [
      { code: '', name: 'Выберите услугу' }, ...Array.from({ length: 80 }, (_, index) => ({ code: String(index + 1), name: `Услуга ${index + 1}` })),
    ] })
    const field = wrapper.get('button')
    expect(field.attributes('aria-label')).toBe('Услуга поставщика')
    expect(field.text()).toContain('Услуга 80')
    await field.trigger('click')
    const menu = document.querySelector('[role="listbox"]')
    expect(menu.style.maxHeight).toBe('248px')
    expect(menu.querySelector('[aria-selected="true"]').textContent).toBe('Услуга 80')
    await field.trigger('keydown', { key: 'Home' })
    await field.trigger('keydown', { key: 'Enter' })
    expect(wrapper.emitted('update:modelValue')).toEqual([['']])
  })

  it('aligns menu with the field below it and changes supplier on click', async () => {
    const wrapper = setup()
    await wrapper.get('button').trigger('click')
    const menu = document.querySelector('[role="listbox"]')
    expect(menu.style.left).toBe('100px')
    expect(menu.style.top).toBe('142px')
    expect(menu.style.width).toBe('160px')
    expect(menu.closest('.modal')).toBeNull()
    menu.querySelectorAll('[role="option"]')[1].click()
    await wrapper.vm.$nextTick()
    expect(wrapper.emitted('update:modelValue')).toEqual([['warehouse']])
    expect(wrapper.emitted('change')).toHaveLength(1)
    expect(document.querySelector('[role="listbox"]')).toBeNull()
  })

  it('opens upward when the field is near the bottom of the window', async () => {
    const wrapper = setup({ left: 100, top: window.innerHeight - 60, bottom: window.innerHeight - 24, width: 160 })
    await wrapper.get('button').trigger('click')
    const menu = document.querySelector('[role="listbox"]')
    expect(menu.style.bottom).toBe('66px')
    expect(menu.style.top).toBe('')
  })

  it('supports keyboard selection and Escape does not close the parent dialog', async () => {
    const wrapper = setup()
    const field = wrapper.get('button')
    field.element.focus()
    await field.trigger('keydown', { key: 'ArrowDown' })
    await field.trigger('keydown', { key: 'ArrowDown' })
    await field.trigger('keydown', { key: 'Enter' })
    expect(wrapper.emitted('update:modelValue')).toEqual([['warehouse']])
    expect(document.activeElement).toBe(field.element)
    await field.trigger('click')
    const outer = vi.fn()
    document.addEventListener('keydown', outer)
    await field.trigger('keydown', { key: 'Escape' })
    document.removeEventListener('keydown', outer)
    expect(outer).not.toHaveBeenCalled()
    expect(field.attributes('aria-expanded')).toBe('false')
  })

  it('does not reload the same supplier and closes on scroll, outside click or disable', async () => {
    const wrapper = setup()
    const field = wrapper.get('button')
    await field.trigger('click')
    document.querySelector('[role="option"]').click()
    await wrapper.vm.$nextTick()
    expect(wrapper.emitted('change')).toBeUndefined()
    await field.trigger('click')
    document.dispatchEvent(new Event('scroll'))
    await wrapper.vm.$nextTick()
    expect(field.attributes('aria-expanded')).toBe('false')
    await field.trigger('click')
    document.body.dispatchEvent(new Event('pointerdown', { bubbles: true }))
    await wrapper.vm.$nextTick()
    expect(field.attributes('aria-expanded')).toBe('false')
    await field.trigger('click')
    await wrapper.setProps({ disabled: true })
    expect(document.querySelector('[role="listbox"]')).toBeNull()
  })
})
