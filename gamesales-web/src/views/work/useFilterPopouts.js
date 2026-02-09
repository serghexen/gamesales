import { onBeforeUnmount, watch } from 'vue'

export function useFilterPopouts({
  activeDealFilter,
  activeGameFilter,
  activeAccountFilter,
}) {
  const onDealFilterOutside = (event) => {
    if (!activeDealFilter.value) return
    const target = event.target
    if (target?.closest?.('.filter-pop') || target?.closest?.('.filter-icon')) return
    activeDealFilter.value = ''
  }

  const onGameFilterOutside = (event) => {
    if (!activeGameFilter.value) return
    const target = event.target
    if (target?.closest?.('.filter-pop') || target?.closest?.('.filter-icon')) return
    activeGameFilter.value = ''
  }

  const onAccountFilterOutside = (event) => {
    if (!activeAccountFilter.value) return
    const target = event.target
    if (target?.closest?.('.filter-pop') || target?.closest?.('.filter-icon')) return
    activeAccountFilter.value = ''
  }

  watch(activeDealFilter, (val) => {
    if (val) {
      window.addEventListener('click', onDealFilterOutside)
    } else {
      window.removeEventListener('click', onDealFilterOutside)
    }
  })

  watch(activeGameFilter, (val) => {
    if (val) {
      window.addEventListener('click', onGameFilterOutside)
    } else {
      window.removeEventListener('click', onGameFilterOutside)
    }
  })

  watch(activeAccountFilter, (val) => {
    if (val) {
      window.addEventListener('click', onAccountFilterOutside)
    } else {
      window.removeEventListener('click', onAccountFilterOutside)
    }
  })

  onBeforeUnmount(() => {
    window.removeEventListener('click', onDealFilterOutside)
    window.removeEventListener('click', onGameFilterOutside)
    window.removeEventListener('click', onAccountFilterOutside)
  })
}
