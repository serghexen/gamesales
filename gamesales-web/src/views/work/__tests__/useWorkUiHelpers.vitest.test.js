import { describe, it, expect } from 'vitest'
import { ref } from 'vue'

import { useWorkUiHelpers } from '../useWorkUiHelpers.js'

function createHarness() {
  const gamesPageSize = ref(20)
  const gamesPageInput = ref(1)
  const accountSort = ref('login_asc')
  const gamesSort = ref({ key: 'title', dir: 'asc' })
  const dealSort = ref({ key: 'created_at', dir: 'desc' })
  const domainsSortAsc = ref(true)

  const api = useWorkUiHelpers({
    gamesPageSize,
    gamesPageInput,
    accountSort,
    gamesSort,
    dealSort,
    domainsSortAsc,
  })

  return {
    api,
    gamesPageSize,
    gamesPageInput,
    accountSort,
    gamesSort,
    dealSort,
    domainsSortAsc,
  }
}

describe('useWorkUiHelpers', () => {
  it('updates games page fields from events', () => {
    const h = createHarness()
    h.api.setGamesPageSizeFromEvent({ target: { value: '50' } })
    h.api.setGamesPageInputFromEvent({ target: { value: '3' } })
    expect(h.gamesPageSize.value).toBe(50)
    expect(h.gamesPageInput.value).toBe(3)

    h.api.setGamesPageSizeFromEvent({ target: { value: '0' } })
    h.api.setGamesPageInputFromEvent({ target: { value: 'bad' } })
    expect(h.gamesPageSize.value).toBe(50)
    expect(h.gamesPageInput.value).toBe(3)
  })

  it('builds sort classes for account/games/deals and keyed sort refs', () => {
    const h = createHarness()
    expect(h.api.getAccountSortClass('login')).toMatchObject({ 'sort-icon--asc': true, 'sort-icon--active': true })
    expect(h.api.getGamesSortClass('title')).toMatchObject({ 'sort-icon--asc': true, 'sort-icon--active': true })
    expect(h.api.getDealSortClass('created_at')).toMatchObject({ 'sort-icon--desc': true, 'sort-icon--active': true })
    expect(h.api.getDomainsSortClass()).toMatchObject({ 'sort-icon--asc': true, 'sort-icon--active': true })
    expect(h.api.getKeyedSortClass(ref({ key: 'code', dir: 'desc' }), 'code')).toMatchObject({ 'sort-icon--desc': true, 'sort-icon--active': true })
  })

  it('formats slot status and note textarea rows', () => {
    const h = createHarness()
    expect(h.api.getSlotAssignmentStatus({ released_at: null })).toBe('Занят')
    expect(h.api.getSlotAssignmentStatus({ released_at: '2026-02-09' })).toBe('Снят')
    expect(h.api.getNotesRows('')).toBe(2)
    expect(h.api.getNotesRows('x'.repeat(200))).toBeGreaterThanOrEqual(3)
    expect(h.api.getCompactNotesRows('')).toBe(2)
    expect(h.api.getCompactNotesRows('x'.repeat(400))).toBeGreaterThanOrEqual(2)
  })
})
