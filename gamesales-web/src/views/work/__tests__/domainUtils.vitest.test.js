import { describe, it, expect } from 'vitest'

import {
  TAB_KEYS,
  maxPrice,
  getMaxDate,
  clampPrice,
  clampPriceFilter,
  formatPrice,
  formatPercent,
  toUtcDateTime,
  mapApiError,
} from '../domainUtils.js'

describe('domainUtils', () => {
  it('TAB_KEYS does not expose removed analytics tab', () => {
    expect(TAB_KEYS).not.toContain('analytics')
    expect(TAB_KEYS).toContain('finance')
  })

  it('getMaxDate returns YYYY-MM-DD format', () => {
    expect(getMaxDate()).toMatch(/^\d{4}-\d{2}-\d{2}$/)
  })

  it('clampPrice keeps value in bounds', () => {
    expect(clampPrice('abc')).toBe(0)
    expect(clampPrice(-12)).toBe(0)
    expect(clampPrice(maxPrice + 1)).toBe(maxPrice)
    expect(clampPrice(150)).toBe(150)
    expect(clampPrice('123.45')).toBe(123.45)
  })

  it('clampPriceFilter returns empty for empty/invalid and string for valid', () => {
    expect(clampPriceFilter('')).toBe('')
    expect(clampPriceFilter(null)).toBe('')
    expect(clampPriceFilter('abc')).toBe('')
    expect(clampPriceFilter(-12)).toBe('0')
    expect(clampPriceFilter(maxPrice + 1)).toBe(String(maxPrice))
  })

  it('formatPrice returns readable value', () => {
    expect(formatPrice('abc')).toBe('—')
    expect(formatPrice(1234.56)).toBe('1 234,56')
  })

  it('formatPercent returns readable percent', () => {
    expect(formatPercent('abc')).toBe('—')
    expect(formatPercent(0.125)).toBe('12,5 %')
  })

  it('toUtcDateTime appends time part', () => {
    expect(toUtcDateTime('2026-02-09')).toBe('2026-02-09T00:00:00Z')
    expect(toUtcDateTime('')).toBeNull()
  })

  it('mapApiError maps free slots message with numbers', () => {
    const msg = 'Not enough free slots. free_slots=2 requested=5'
    expect(mapApiError(msg)).toBe('Недостаточно свободных слотов: свободно 2, нужно 5')
  })

  it('mapApiError maps known messages and keeps unknown text', () => {
    expect(mapApiError('slot_type_code is required for rental')).toBe('Для шеринга нужно выбрать тип слота')
    expect(mapApiError('order_number must be unique for source ym/ozon/wb')).toBe('Для источников ym/ozon/wb номер заказа уже используется')
    expect(mapApiError('draft deal cannot be completed directly')).toBe('Черновик нельзя сразу перевести в статус Завершен')
    expect(mapApiError('deal was modified by another user')).toBe('Сделка уже изменена другим пользователем. Обновите список и попробуйте снова')
    expect(mapApiError('is_refund can be changed only for pending deals')).toBe('Признак возврата можно менять только у сделки в ожидании')
    expect(mapApiError('не достаточно прав для проведения возврата')).toBe('не достаточно прав для проведения возврата')
    expect(mapApiError('query.payload: Field required')).toBe('Некорректный формат запроса. Обновите страницу и попробуйте снова')
    expect(mapApiError('Load failed')).toBe('Не удалось отправить файл. Проверьте формат (.xlsx/.xls) и доступность API')
    expect(mapApiError('Account already exists')).toBe('Данный аккаунт уже есть в базе данных')
    expect(mapApiError('duplicate key value violates unique constraint "uq_account_login"')).toBe('Данный аккаунт уже есть в базе данных')
    expect(mapApiError('System type cannot be deleted')).toBe('Системный тип нельзя удалить')
    expect(mapApiError('Type has active sections')).toBe('Нельзя удалить тип: к нему привязаны разделы')
    expect(mapApiError('Operation has entries and cannot be deleted')).toBe('Нельзя удалить вид операции: по нему уже есть записи')
    expect(mapApiError('Type has operations and cannot be deleted')).toBe('Нельзя удалить тип: к нему привязаны виды операций')
    expect(mapApiError('Entry not found')).toBe('Проводка не найдена')
    expect(mapApiError('custom backend error')).toBe('custom backend error')
    expect(mapApiError('')).toBe('Ошибка')
  })
})
