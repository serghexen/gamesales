import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import WorkSupplierCatalog from '../sections/WorkSupplierCatalog.vue'
import { apiGet, apiPost } from '../../../api/http'
vi.mock('../../../api/http', () => ({ apiGet: vi.fn(), apiPost: vi.fn() }))
const row = (id, extra = {}) => ({ service_id: '1', nominal_id: String(id), service_title: 'Blizzard', nominal_title: `EUR ${id}`, service_type: 'VOUCHER', price: null, stock_count: 0, status: 'active', reviewed_at: null, review_reason: 'new', review_revision: 2, linked: false, ...extra })
function button(wrapper, text) {
  // Ищем действие по видимому названию, не завися от количества кнопок в соседней форме покупки.
  return wrapper.findAll('button').find(item => item.text() === text)
}
beforeEach(() => { vi.clearAllMocks(); apiGet.mockResolvedValue({ items: [row(20), row(50, { reviewed_at: '2026-09-22', linked: true, status: 'unavailable' })], offline: true }); apiPost.mockResolvedValue({ ok: true }) })
describe('Список ваучеров', () => {
  it('открывает блок свёрнутым при каждом входе, а обновление данных не раскрывает его', async () => {
    // Возврат во вкладку пересоздаёт компонент; состояние раскрытия не переносится.
    const wrapper = mount(WorkSupplierCatalog, { props: { token: 'test' } })
    await flushPromises()
    expect(wrapper.get('details').element.open).toBe(false)
    await wrapper.setProps({ refreshState: 'completed' })
    await flushPromises()
    expect(wrapper.get('details').element.open).toBe(false)
    wrapper.get('details').element.open = true
    wrapper.unmount()
    const reopened = mount(WorkSupplierCatalog, { props: { token: 'test' } })
    await flushPromises()
    expect(reopened.get('details').element.open).toBe(false)
    reopened.unmount()
  })
  it('сбрасывает внутреннюю прокрутку при переходе страницы и смене фильтра', async () => {
    // Навигация остаётся снаружи списка, а следующая выборка начинается сверху.
    apiGet.mockResolvedValue({ items: Array.from({ length: 30 }, (_, i) => row(i + 1)) })
    const wrapper = mount(WorkSupplierCatalog, { props: { token: 'test', canReview: true } })
    await flushPromises()
    wrapper.get('details').element.open = true
    const viewport = wrapper.get('[aria-label="Список ваучеров"]')
    expect(viewport.attributes('tabindex')).toBe('0')
    viewport.element.scrollTop = 250
    await button(wrapper, 'Далее').trigger('click')
    await flushPromises()
    expect(viewport.element.scrollTop).toBe(0)
    expect(wrapper.find('tbody tr').text()).toContain('EUR 26')
    viewport.element.scrollTop = 120
    await button(wrapper, 'Не связаны').trigger('click')
    await flushPromises()
    expect(viewport.element.scrollTop).toBe(0)
    expect(wrapper.find('tbody tr').text()).toContain('EUR 1')
    expect(viewport.find('nav').exists()).toBe(false)
  })
  it('убирает пустую колонку действий у уже просмотренных строк', async () => {
    // Сохранённые просмотренные позиции не оставляют широкий пустой столбец справа.
    apiGet.mockResolvedValue({ items: [row(20, { reviewed_at: '2026-09-22' })] })
    const wrapper = mount(WorkSupplierCatalog, { props: { token: 'test', canReview: true } })
    await flushPromises()
    expect(wrapper.findAll('thead th')).toHaveLength(4)
    expect(wrapper.findAll('tbody td')).toHaveLength(4)
  })
  it('читает БД, сохраняет нулевой остаток и отделяет неизвестную цену', async () => {
    const wrapper = mount(WorkSupplierCatalog, { props: { token: 'test', canReview: true } })
    await flushPromises()
    expect(apiGet).toHaveBeenCalledWith('/integrations/interhub/catalog/current', { token: 'test' })
    expect(wrapper.text()).not.toContain('Проверка staging')
    const cells = wrapper.find('tbody tr').findAll('td')
    expect(cells[2].find('strong').text()).toBe('—')
    expect(cells[3].find('strong').text()).toBe('0')
    expect(apiPost).not.toHaveBeenCalled()
  })
  it('не снимает Новое после перечитывания и не смешивает его с привязкой', async () => {
    const wrapper = mount(WorkSupplierCatalog, { props: { token: 'test', canReview: true } })
    await flushPromises()
    await button(wrapper, 'Новые').trigger('click')
    expect(wrapper.findAll('tbody tr')).toHaveLength(1)
    await wrapper.get('[aria-label="Перечитать сохранённые позиции"]').trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('Новое')
    expect(apiPost).not.toHaveBeenCalled()
    await button(wrapper, 'Недоступны').trigger('click')
    expect(wrapper.find('tbody tr').text()).toContain('EUR 50')
  })
  it('отмечает только видимые строки с версией и не делает опрос', async () => {
    const wrapper = mount(WorkSupplierCatalog, { props: { token: 'test', canReview: true } })
    await flushPromises()
    await button(wrapper, 'Просмотрено').trigger('click')
    await flushPromises()
    expect(apiPost).toHaveBeenCalledWith('/integrations/interhub/catalog/review', [{ service_id: '1', nominal_id: '20', review_revision: 2 }], { token: 'test' })
    expect(apiGet.mock.calls.every(([url]) => url.endsWith('/catalog/current'))).toBe(true)
  })
  it('ограничивает массовую отметку текущей страницей и скрывает её без прав', async () => {
    apiGet.mockResolvedValue({ items: Array.from({ length: 30 }, (_, i) => row(i + 1)) })
    const wrapper = mount(WorkSupplierCatalog, { props: { token: 'test', canReview: true } })
    await flushPromises()
    await button(wrapper, 'Отметить страницу просмотренной').trigger('click')
    await flushPromises()
    expect(apiPost.mock.calls[0][1]).toHaveLength(25)
    await wrapper.setProps({ canReview: false })
    expect(button(wrapper, 'Просмотрено')).toBeUndefined()
  })
})
