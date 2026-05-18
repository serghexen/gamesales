import { computed, watch } from 'vue'

export function useProductsViewState({
  products,
  productsTotal,
  productsPage,
  productsPageInput,
  productsPageSize,
  loadProducts,
  productAccounts,
  productAccountsSort,
  productAccountsPage,
  productAccountsPageSize,
}) {
  // Количество страниц в списке игр.
  const productsTotalPages = computed(() => {
    const pages = Math.ceil(productsTotal.value / productsPageSize.value)
    return pages > 0 ? pages : 1
  })

  // Локально можно расширить сортировку игр, сейчас отдаем как есть.
  const sortedProducts = computed(() => [...products.value])
  const pagedProducts = computed(() => sortedProducts.value)

  // Если страниц стало меньше, держим текущую страницу в рамках.
  watch(productsTotalPages, (total) => {
    if (productsPage.value <= total) return
    // Если после фильтрации ушли на несуществующую страницу, догружаем последнюю доступную.
    productsPage.value = total
    if (productsTotal.value > 0) {
      loadProducts()
    }
  })

  // Синхронизируем поле ввода страницы и реальную страницу.
  watch(productsPage, (val) => {
    productsPageInput.value = val
  })

  // При смене размера страницы перезагружаем список с первой страницы.
  watch(productsPageSize, () => {
    productsPage.value = 1
    loadProducts()
  })

  // Сортировка аккаунтов внутри модалки игры.
  const sortedProductAccounts = computed(() => {
    const list = [...productAccounts.value]
    const { key, dir } = productAccountsSort.value
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

  // Количество страниц в таблице аккаунтов игры.
  const productAccountsTotalPages = computed(() => {
    const pages = Math.ceil(sortedProductAccounts.value.length / productAccountsPageSize)
    return pages > 0 ? pages : 1
  })

  // Не даем локальной пагинации аккаунтов товара выйти за пределы.
  watch(productAccountsTotalPages, (total) => {
    if (productAccountsPage.value > total) {
      productAccountsPage.value = total
    }
  })

  // Текущая страница аккаунтов игры.
  const pagedProductAccounts = computed(() => {
    const start = (productAccountsPage.value - 1) * productAccountsPageSize
    return sortedProductAccounts.value.slice(start, start + productAccountsPageSize)
  })

  return {
    productsTotalPages,
    sortedProducts,
    pagedProducts,
    productAccountsTotalPages,
    pagedProductAccounts,
  }
}
