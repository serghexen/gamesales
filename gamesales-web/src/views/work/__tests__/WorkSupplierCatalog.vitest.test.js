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
  it('отделяет актуальный каталог от событий и не скрывает нулевой остаток или ошибку опроса', async () => {
    // Остаток и ошибки не означают исчезновение; старые позиции не засоряют подбор несвязанных.
    apiGet.mockResolvedValue({ items: [
      row(1, { reviewed_at: '2026-09-23', stock_count: 0, price_error: 'Ошибка' }),
      row(2, { linked: true }),
      row(3, { status: 'suspect', review_reason: 'missing', missing_count: 1 }),
      row(4, { status: 'unavailable', review_reason: 'missing', reviewed_at: '2026-09-23' }),
      row(5, { status: 'unavailable', review_reason: 'changed', availability_reason: 'nominal_disabled' }),
    ] })
    const wrapper = mount(WorkSupplierCatalog, { props: { token: 'test' } })
    await flushPromises()
    expect(wrapper.get('summary').text()).toContain('Актуальных: 2')
    expect(wrapper.get('summary').text()).toContain('Новых: 1')
    expect(wrapper.get('summary').text()).toContain('Изменений: 2')
    expect(wrapper.findAll('tbody tr')).toHaveLength(2)
    expect(wrapper.find('tbody').text()).toContain('EUR 1')
    await button(wrapper, 'Не связаны').trigger('click')
    expect(wrapper.findAll('tbody tr')).toHaveLength(1)
    expect(wrapper.find('tbody').text()).toContain('EUR 1')
    await button(wrapper, 'Изменения').trigger('click')
    expect(wrapper.findAll('tbody tr')).toHaveLength(2)
    expect(wrapper.find('tbody').text()).toContain('EUR 3')
    expect(wrapper.find('tbody').text()).toContain('EUR 5')
    expect(wrapper.find('tbody').text()).not.toContain('EUR 4')
  })
  it('убирает исчезнувшую позицию после просмотра и показывает её возвращение как изменение', async () => {
    // Та же запись возвращается в актуальные позиции без повторной отметки «Новое».
    const missing = row(50, { status: 'unavailable', review_reason: 'missing', missing_count: 2 })
    apiGet.mockResolvedValue({ items: [row(20), missing] })
    const wrapper = mount(WorkSupplierCatalog, { props: { token: 'test', canReview: true } })
    await flushPromises()
    await button(wrapper, 'Изменения').trigger('click')
    apiGet.mockResolvedValue({ items: [row(20), { ...missing, reviewed_at: '2026-09-23' }] })
    await button(wrapper, 'Просмотрено').trigger('click')
    await flushPromises()
    expect(wrapper.get('summary').text()).not.toContain('Изменений:')
    for (const label of ['Изменения', 'Недоступны', 'Все актуальные', 'Не связаны']) {
      await button(wrapper, label).trigger('click')
      expect(wrapper.find('tbody').text()).not.toContain('EUR 50')
    }
    apiGet.mockResolvedValue({ items: [row(20), row(50, {
      review_reason: 'changed', review_revision: 3, review_before: { status: 'unavailable' },
    })] })
    await wrapper.get('[aria-label="Перечитать сохранённые позиции"]').trigger('click')
    await flushPromises()
    await button(wrapper, 'Все актуальные').trigger('click')
    expect(wrapper.find('tbody').text()).toContain('EUR 50')
    await button(wrapper, 'Изменения').trigger('click')
    expect(wrapper.find('tbody').text()).toContain('Доступность: Недоступен → Доступен')
    await button(wrapper, 'Новые').trigger('click')
    expect(wrapper.find('tbody').text()).not.toContain('EUR 50')
  })
  it('показывает прежние и текущие названия и доступность в изменениях', async () => {
    // Несколько изменений до просмотра отображаются вместе; текст поставщика выводится безопасно.
    apiGet.mockResolvedValue({ items: [row(20, { review_reason: 'changed', service_title: 'Blizzard EUR',
      nominal_title: '<b>EUR 25</b>', review_before: { service_title: 'Blizzard', nominal_title: 'EUR 20', status: 'unavailable' },
      changes_detected_at: '2026-09-23T06:00:00Z' })] })
    const wrapper = mount(WorkSupplierCatalog, { props: { token: 'test', canReview: true } })
    await flushPromises()
    await button(wrapper, 'Изменения').trigger('click')
    expect(wrapper.text()).toContain('Услуга: «Blizzard» → «Blizzard EUR»')
    expect(wrapper.text()).toContain('Номинал: «EUR 20» → «<b>EUR 25</b>»')
    expect(wrapper.text()).toContain('Доступность: Недоступен → Доступен')
    expect(wrapper.text()).toContain('Обнаружено:')
    expect(wrapper.find('tbody b').exists()).toBe(false)
  })
  it('объясняет непросмотренную пропажу и отключение, скрывая уже просмотренные события', async () => {
    // Недоступные позиции видны в уведомлениях, пока оператор не просмотрит событие.
    apiGet.mockResolvedValue({ items: [
      row(1, { status: 'suspect', missing_count: 1, review_reason: 'missing' }),
      row(2, { status: 'unavailable', missing_count: 3, review_reason: 'missing', reviewed_at: '2026-09-23', last_seen_at: '2026-09-22T06:00:00Z' }),
      row(3, { status: 'unavailable', availability_reason: 'service_disabled' }),
      row(4, { status: 'unavailable', availability_reason: 'nominal_disabled' }),
      row(5, { price_error: 'Ошибка цены', stock_error: 'Ошибка остатка' }),
    ] })
    const wrapper = mount(WorkSupplierCatalog, { props: { token: 'test' } })
    await flushPromises()
    await button(wrapper, 'Недоступны').trigger('click')
    expect(wrapper.findAll('tbody tr')).toHaveLength(3)
    expect(wrapper.text()).toContain('Ждём повторной проверки.')
    expect(wrapper.text()).not.toContain('Проверок подряд: 3.')
    expect(wrapper.text()).not.toContain('Последний раз видели:')
    expect(wrapper.text()).toContain('Поставщик отключил услугу.')
    expect(wrapper.text()).toContain('Поставщик отключил номинал.')
    await button(wrapper, 'Все актуальные').trigger('click')
    expect(wrapper.findAll('tbody tr')).toHaveLength(1)
    expect(wrapper.find('tbody').text()).toContain('EUR 5')
    expect(wrapper.find('tbody').text()).not.toContain('Недоступен')
  })
  it('не придумывает прежние названия для старых отметок и скрывает подробности после просмотра', async () => {
    // Старые данные не содержат снимка до изменения, но новые отметки очищаются обычным действием.
    apiGet.mockResolvedValue({ items: [row(20, { review_reason: 'changed' })] })
    const wrapper = mount(WorkSupplierCatalog, { props: { token: 'test', canReview: true } })
    await flushPromises()
    expect(wrapper.text()).toContain('прежние значения не сохранены')
    apiGet.mockResolvedValue({ items: [row(20, { review_reason: 'changed', reviewed_at: '2026-09-23' })] })
    await button(wrapper, 'Просмотрено').trigger('click')
    await flushPromises()
    expect(wrapper.find('.supplier-current__changes').exists()).toBe(false)
    await button(wrapper, 'Изменения').trigger('click')
    expect(wrapper.text()).toContain('Нет позиций по выбранному фильтру')
  })
  it('объясняет возврат к прежним значениям между просмотрами', async () => {
    // Возврат после временного исчезновения не оставляет непонятное «Есть изменения» без пояснения.
    apiGet.mockResolvedValue({ items: [row(20, { review_reason: 'changed', availability_reason: '',
      review_before: { service_title: 'Blizzard', nominal_title: 'EUR 20', status: 'active', availability_reason: '' } })] })
    const wrapper = mount(WorkSupplierCatalog, { props: { token: 'test' } })
    await flushPromises()
    expect(wrapper.text()).toContain('Данные менялись и вернулись к прежним значениям.')
  })
  it('показывает обе причины при изменении причины недоступности', async () => {
    // Один и тот же статус может означать разные действия поставщика.
    apiGet.mockResolvedValue({ items: [row(20, { status: 'unavailable', review_reason: 'changed', availability_reason: 'nominal_disabled',
      review_before: { status: 'unavailable', availability_reason: 'service_disabled' } })] })
    const wrapper = mount(WorkSupplierCatalog, { props: { token: 'test' } })
    await flushPromises()
    await button(wrapper, 'Изменения').trigger('click')
    expect(wrapper.text()).toContain('Причина: Поставщик отключил услугу → Поставщик отключил номинал')
  })
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
    expect(wrapper.find('tbody tr').text()).toContain('Нет позиций по выбранному фильтру')
    await button(wrapper, 'Все актуальные').trigger('click')
    expect(wrapper.text()).not.toContain('EUR 50')
  })
  it('после просмотра недоступной позиции убирает уведомление, сохраняя новые позиции', async () => {
    // Новый товар остаётся новым, а просмотренная недоступность снова показывается только после нового события.
    const unavailable = row(50, { status: 'unavailable', review_reason: 'missing', missing_count: 2 })
    apiGet.mockResolvedValue({ items: [row(20), unavailable] })
    const wrapper = mount(WorkSupplierCatalog, { props: { token: 'test', canReview: true } })
    await flushPromises()
    await button(wrapper, 'Недоступны').trigger('click')
    apiGet.mockResolvedValue({ items: [row(20), { ...unavailable, reviewed_at: '2026-09-23' }] })
    await button(wrapper, 'Просмотрено').trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('Нет позиций по выбранному фильтру')
    await button(wrapper, 'Новые').trigger('click')
    expect(wrapper.find('tbody tr').text()).toContain('EUR 20')
    apiGet.mockResolvedValue({ items: [row(20), { ...unavailable, review_revision: 3 }] })
    await wrapper.get('[aria-label="Перечитать сохранённые позиции"]').trigger('click')
    await flushPromises()
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
