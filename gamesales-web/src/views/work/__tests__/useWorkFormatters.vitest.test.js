import { describe, it, expect } from 'vitest'
import { ref } from 'vue'

import { useWorkFormatters } from '../useWorkFormatters.js'

function createHarness() {
  return useWorkFormatters({
    accountsAll: ref([
      { account_id: 1, login_full: 'user@domain' },
      { account_id: 2, login_name: 'just_user' },
    ]),
    regions: ref([{ code: 'RU', name: 'Россия' }]),
    domains: ref([{ name: 'gmail.com' }]),
    sources: ref([{ source_id: 10, code: 'tg', name: 'Telegram' }]),
    dealFlowStatusOptions: [{ code: 'pending', name: 'В ожидании' }],
    maxProductTitleLength: 10,
  })
}

describe('useWorkFormatters', () => {
  it('returns labels with fallback values', () => {
    const f = createHarness()
    expect(f.getAccountLabelById(1)).toBe('user@domain')
    expect(f.getAccountLabelById('1')).toBe('user@domain')
    expect(f.getAccountLabelById(2)).toBe('just_user')
    expect(f.getAccountLabelById(999)).toBe('999')
    expect(f.getRegionLabel('RU')).toBe('Россия (RU)')
    expect(f.getRegionLabel('XX')).toBe('XX')
    expect(f.getDomainLabel('gmail.com')).toBe('gmail.com')
    expect(f.getSourceLabelById(10)).toBe('Telegram (tg)')
    expect(f.getSourceLabelById(99)).toBe('99')
    expect(f.getFlowStatusLabel('pending')).toBe('В ожидании')
    expect(f.getFlowStatusLabel('other')).toBe('other')
  })

  it('builds display and tooltip for deal product title', () => {
    const f = createHarness()
    const dealLong = { product_title: 'Very Long Game Title', product_short_title: 'VLGT' }
    const dealShort = { product_title: 'Short', product_short_title: 'S' }

    expect(f.getDealProductTitleDisplay(dealLong)).toBe('VLGT')
    expect(f.getDealProductTitleTooltip(dealLong)).toBe('Very Long Game Title')
    expect(f.getDealProductTitleDisplay(dealShort)).toBe('Short')
    expect(f.getDealProductTitleTooltip(dealShort)).toBe('')
  })

  it('formats utility values', () => {
    const f = createHarness()
    expect(f.formatProductPlatforms(['ps4', 'ps5'])).toBe('ps4, ps5')
    expect(f.formatProductPlatforms([])).toBe('—')
    expect(f.formatSecret('abc')).toBe('abc')
    expect(f.formatSecret('')).toBe('—')
    expect(f.getAccountStatusLabel('active')).toBe('active')
    expect(f.getAccountStatusLabel('')).toBe('—')
  })

  it('formats date helpers safely', () => {
    const f = createHarness()
    expect(f.formatDateOnly('bad-date')).toBe('—')
    expect(f.formatDateOnly('2026-02-09T10:15:00Z')).toMatch(/\d/)
    expect(f.formatDateTimeMinutes('bad-date')).toBe('—')
    expect(f.formatDateTimeMinutes('2026-02-09T10:15:00Z')).toMatch(/\d/)
  })
})
