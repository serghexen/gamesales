import { onBeforeUnmount, watch } from 'vue'

export function useFilterPopouts({
  activeDealFilter,
  activeProductFilter,
  activeGameFilter,
  activeAccountFilter,
}) {
  const onDealFilterOutside = (event) => {
    if (!activeDealFilter.value) return
    const target = event.target
    if (target?.closest?.('.filter-pop') || target?.closest?.('.filter-icon')) return
    activeDealFilter.value = ''
  }

  // Поддерживаем новый product-фильтр и старое имя game-фильтра для совместимости.
  const resolvedProductFilter = activeProductFilter || activeGameFilter

  const onProductFilterOutside = (event) => {
    if (!resolvedProductFilter?.value) return
    const target = event.target
    if (target?.closest?.('.filter-pop') || target?.closest?.('.filter-icon')) return
    resolvedProductFilter.value = ''
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

  if (resolvedProductFilter) {
    // Навешиваем обработчик только когда реально передан источник для watch.
    watch(resolvedProductFilter, (val) => {
      if (val) {
        window.addEventListener('click', onProductFilterOutside)
      } else {
        window.removeEventListener('click', onProductFilterOutside)
      }
    })
  }

  watch(activeAccountFilter, (val) => {
    if (val) {
      window.addEventListener('click', onAccountFilterOutside)
    } else {
      window.removeEventListener('click', onAccountFilterOutside)
    }
  })

  onBeforeUnmount(() => {
    window.removeEventListener('click', onDealFilterOutside)
    window.removeEventListener('click', onProductFilterOutside)
    window.removeEventListener('click', onAccountFilterOutside)
  })
}
