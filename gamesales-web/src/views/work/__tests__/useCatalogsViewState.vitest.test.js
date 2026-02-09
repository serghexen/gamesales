import { describe, it, expect } from 'vitest'
import { ref } from 'vue'

import { useCatalogsViewState } from '../useCatalogsViewState.js'

function createHarness() {
  return useCatalogsViewState({
    users: ref([
      { username: 'b', created_at: '2026-01-01T00:00:00Z' },
      { username: 'a', created_at: '2026-02-01T00:00:00Z' },
    ]),
    usersSort: ref({ key: 'created_at', dir: 'desc' }),
    domains: ref([{ name: 'z.com' }, { name: 'a.com' }]),
    domainsSortAsc: ref(true),
    sources: ref([
      { code: 'zz', name: 'Zeta' },
      { code: 'aa', name: 'Alpha' },
    ]),
    sourcesSort: ref({ key: 'name', dir: 'asc' }),
    platforms: ref([
      { code: 'ps4', rank: 2 },
      { code: 'ps5', rank: 1 },
    ]),
    platformsSort: ref({ key: 'rank', dir: 'asc' }),
    regions: ref([{ code: 'US', name: 'USA' }, { code: 'RU', name: 'Russia' }]),
    regionsSort: ref({ key: 'code', dir: 'asc' }),
  })
}

describe('useCatalogsViewState', () => {
  it('sorts users by selected key and direction', () => {
    const s = createHarness()
    expect(s.sortedUsers.value.map((u) => u.username)).toEqual(['a', 'b'])
  })

  it('sorts domains and sources', () => {
    const s = createHarness()
    expect(s.sortedDomains.value.map((d) => d.name)).toEqual(['a.com', 'z.com'])
    expect(s.sortedSources.value.map((d) => d.name)).toEqual(['Alpha', 'Zeta'])
    expect(s.sourcesByCode.value.map((d) => d.code)).toEqual(['aa', 'zz'])
  })

  it('sorts platforms and regions', () => {
    const s = createHarness()
    expect(s.sortedPlatforms.value.map((p) => p.code)).toEqual(['ps5', 'ps4'])
    expect(s.sortedRegions.value.map((r) => r.code)).toEqual(['RU', 'US'])
  })
})
