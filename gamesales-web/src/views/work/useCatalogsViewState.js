import { computed } from 'vue'

export function useCatalogsViewState({
  users,
  usersSort,
  domains,
  domainsSortAsc,
  sources,
  sourcesSort,
  platforms,
  platformsSort,
  regions,
  regionsSort,
}) {
  // Сортировка пользователей в таблице.
  const sortedUsers = computed(() => {
    const list = [...users.value]
    const { key, dir } = usersSort.value
    list.sort((a, b) => {
      const av = key === 'created_at' ? new Date(a.created_at || 0).getTime() : a[key]
      const bv = key === 'created_at' ? new Date(b.created_at || 0).getTime() : b[key]
      if (typeof av === 'number' && typeof bv === 'number') {
        return dir === 'asc' ? av - bv : bv - av
      }
      return dir === 'asc'
        ? String(av || '').localeCompare(String(bv || ''))
        : String(bv || '').localeCompare(String(av || ''))
    })
    return list
  })

  // Сортировка доменов.
  const sortedDomains = computed(() => {
    const list = [...domains.value]
    list.sort((a, b) =>
      domainsSortAsc.value
        ? String(a.name || '').localeCompare(String(b.name || ''))
        : String(b.name || '').localeCompare(String(a.name || ''))
    )
    return list
  })

  // Сортировка источников.
  const sortedSources = computed(() => {
    const list = [...sources.value]
    const { key, dir } = sourcesSort.value
    list.sort((a, b) => {
      const av = a[key]
      const bv = b[key]
      return dir === 'asc'
        ? String(av || '').localeCompare(String(bv || ''))
        : String(bv || '').localeCompare(String(av || ''))
    })
    return list
  })

  // Источники, отсортированные по коду (удобно для выбора в формах).
  const sourcesByCode = computed(() => {
    const list = [...sources.value]
    list.sort((a, b) => String(a.code || '').localeCompare(String(b.code || '')))
    return list
  })

  // Сортировка платформ.
  const sortedPlatforms = computed(() => {
    const list = [...platforms.value]
    const { key, dir } = platformsSort.value
    list.sort((a, b) => {
      const av = a[key]
      const bv = b[key]
      if (typeof av === 'number' && typeof bv === 'number') {
        return dir === 'asc' ? av - bv : bv - av
      }
      return dir === 'asc'
        ? String(av || '').localeCompare(String(bv || ''))
        : String(bv || '').localeCompare(String(av || ''))
    })
    return list
  })

  // Сортировка регионов.
  const sortedRegions = computed(() => {
    const list = [...regions.value]
    const { key, dir } = regionsSort.value
    list.sort((a, b) => {
      const av = a[key]
      const bv = b[key]
      return dir === 'asc'
        ? String(av || '').localeCompare(String(bv || ''))
        : String(bv || '').localeCompare(String(av || ''))
    })
    return list
  })

  return {
    sortedUsers,
    sortedDomains,
    sortedSources,
    sourcesByCode,
    sortedPlatforms,
    sortedRegions,
  }
}
