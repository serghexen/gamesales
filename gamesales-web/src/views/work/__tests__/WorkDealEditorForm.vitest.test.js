import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

describe('WorkDealEditorForm template', () => {
  function readTemplateSource() {
    const filePath = resolve(process.cwd(), 'src/views/work/sections/WorkDealEditorForm.vue')
    return readFileSync(filePath, 'utf8')
  }

  it('does not render slot helper blocks in sharing forms', () => {
    const source = readTemplateSource()

    expect(source).not.toContain('Слоты аккаунта (занято)')
    expect(source).not.toContain('<div class="slot-status__title">Слоты</div>')
  })

  it('uses games as default product type in sharing create form', () => {
    const source = readTemplateSource()
    const createFilterSelect = source.match(/<select v-model="newDealProductTypeFilter"[\s\S]*?<\/select>/)?.[0] || ''
    const editFilterSelect = source.match(/<select v-else v-model="editDealProductTypeFilter"[\s\S]*?<\/select>/)?.[0] || ''

    expect(source).toContain("const newDealProductTypeFilter = ref('game')")
    expect(source).toContain("const editDealProductTypeFilter = ref('game')")
    expect(source).toContain("newDealProductTypeFilter.value = 'game'")
    expect(createFilterSelect).toContain('<option value="game">Игра</option>')
    expect(createFilterSelect).toContain('<option value="subscription">Подписка</option>')
    expect(createFilterSelect).not.toContain('value="all"')
    expect(editFilterSelect).toContain('<option value="game">Игра</option>')
    expect(editFilterSelect).toContain('<option value="subscription">Подписка</option>')
    expect(editFilterSelect).not.toContain('value="all"')
  })

  it('renders rental slot type in right column рядом с типом товара', () => {
    const source = readTemplateSource()
    const newRentalMain = source.match(/<div class="deal-form__rental-main">[\s\S]*?<label class="field field--sharing-account">/)?.[0] || ''
    const newRentalSide = source.match(/<div class="deal-form__rental-side">[\s\S]*?<label class="field">[\s\S]*?{{ showNewDealProductSearch \? 'Поиск' : 'Товар' }}/)?.[0] || ''
    const rentalLayouts = source.match(/class="deal-form__rental-layout"/g) || []

    expect(source).toContain('deal-form__rental-main')
    expect(source).toContain('deal-form__rental-side')
    expect(rentalLayouts.length).toBeGreaterThanOrEqual(2)
    expect(source).toContain('<span class="label">Тип слота</span>')
    expect(source).toContain('<span class="label">Ответственный</span>')
    expect(newRentalMain).toContain('<span class="label">Ответственный</span>')
    expect(newRentalMain).not.toContain('<span class="label">Тип слота</span>')
    expect(newRentalSide).toContain('<span class="label">Тип товара</span>')
    expect(newRentalSide).toContain('<span class="label">Тип слота</span>')
    expect(source).toContain('selectedEditDealProductTypeLabel')
  })

  it('renders sharing product list without title label and with balanced height class', () => {
    const source = readTemplateSource()

    expect(source).not.toContain('<span class="label">Список игр</span>')
    expect(source).toContain('field--sharing-product-list')
    expect(source).toContain('field--sharing-product-list--selected')
    expect(source).toContain('input--list--sharing-height')
    expect(source).toContain('input--list--compact')
    expect(source).toContain(':size="newDeal.product_id ? 1 : 3"')
  })

  it('uses slot-first flow controls for subscriptions in create and edit', () => {
    const source = readTemplateSource()

    expect(source).toContain("v-if=\"!showNewDealProductNoMatches\"")
    expect(source).toContain("v-if=\"!showEditDealProductNoMatches\"")
    expect(source).toContain('isNewRentalSubscriptionMode && !newDeal.slot_type_code')
    expect(source).toContain('isEditRentalSubscriptionMode && !editDeal.slot_type_code')
    expect(source).toContain("getSlotTypeOptionsForDeal('new')")
    expect(source).toContain("getSlotTypeOptionsForDeal('edit')")
    expect(source).toContain('subscriptionFreeProductIdsEdit')
    expect(source).toContain('subscriptionFreeProductIdsNew')
    expect(source).toContain('hasFreeSubscriptionSlotByProductId')
  })

  it('shows subscription search only between slot selection and product selection', () => {
    const source = readTemplateSource()

    expect(source).toContain('const showEditDealProductSearch = computed(() => {')
    expect(source).toContain('const showNewDealProductSearch = computed(() => {')
    expect(source).toContain("editDealProductTypeFilter.value === 'subscription'")
    expect(source).toContain("newDealProductTypeFilter.value === 'subscription'")
    expect(source).toContain('!!editDeal.value?.slot_type_code && !editDeal.value?.product_id')
    expect(source).toContain('!!newDeal.value?.slot_type_code && !newDeal.value?.product_id')
    expect(source).toContain('v-else-if="showEditDealProductSearch"')
    expect(source).toContain('v-if="showNewDealProductSearch"')
    expect(source).toContain('v-else')
    expect(source).toContain("{{ showNewDealProductSearch ? 'Поиск' : 'Товар' }}")
  })

  it('renders quick create blocks as collapsible toggles', () => {
    const source = readTemplateSource()
    const newRentalMain = source.match(/<div class="deal-form__rental-main">[\s\S]*?<div class="deal-form__rental-side">/)?.[0] || ''
    const newRentalSide = source.match(/<div class="deal-form__rental-side">[\s\S]*?<\/div>\s*<\/div>\s*<div v-if="newDeal\.deal_type_code === 'sale'"/)?.[0] || ''

    expect(source).toContain("const editQuickProductOpen = ref(false)")
    expect(source).toContain("const editQuickAccountOpen = ref(false)")
    expect(source).toContain("const newQuickProductOpen = ref(false)")
    expect(source).toContain("const newQuickAccountOpen = ref(false)")
    expect(source).toContain("'+ Быстрое создание товара'")
    expect(source).toContain("'+ Быстрое создание аккаунта'")
    expect(source).toContain('v-if="editQuickProductOpen"')
    expect(source).toContain('v-if="editQuickAccountOpen"')
    expect(source).toContain('v-if="newQuickProductOpen"')
    expect(source).toContain('v-if="newQuickAccountOpen"')
    expect(source).toContain('quick-create quick-create--account')
    expect(source).toContain('<div class="quick-create__header">')
    expect(source).toContain('check-list check-list--compact check-list--platform-row')
    expect(source).not.toContain('quick-create__actions')
    expect(newRentalMain).not.toContain('newQuickAccountOpen ? \'Быстрое создание аккаунта\'')
    expect(newRentalSide).toContain('newQuickAccountOpen ? \'Быстрое создание аккаунта\'')
  })

  it('shows login, password and reserve fields under selected sharing account', () => {
    const source = readTemplateSource()
    const newRentalMain = source.match(/<div class="deal-form__rental-main">[\s\S]*?<div class="deal-form__rental-side">/)?.[0] || ''
    const newRentalSide = source.match(/<div class="deal-form__rental-side">[\s\S]*?<\/div>\s*<\/div>\s*<div v-if="newDeal\.deal_type_code === 'sale'"/)?.[0] || ''

    expect(source).toContain('v-if="editDeal.account_id"')
    expect(source).toContain('getAccountPasswordById(editDeal.account_id)')
    expect(source).toContain('getDealReserveLabel(editDeal.account_id, editDeal.reserve_key, editDeal.deal_id)')
    expect(source).toContain('v-if="newDeal.account_id"')
    expect(source).toContain('getAccountPasswordById(newDeal.account_id)')
    expect(source).toContain('getDealReserveLabel(newDeal.account_id, newDeal.reserve_key)')
    expect(source).toContain('deal-form__account-details-head')
    expect(source).toContain('Данные аккаунта')
    expect(source).toContain('const value = String(getAccountSecret.value?.(accountId) || \'\').trim()')
    expect(source).toContain('function getUsedReserveKeysByAccount(accountId, currentDealId = null)')
    expect(source).toContain('const entries = Array.isArray(getReserveSecretEntries.value?.(accountId))')
    expect(source).not.toContain('deal-form__account-details">\n                          <div class="deal-form__double">')
    expect(source).toContain('deal-form__account-details-head">Данные аккаунта</div>')
    expect(newRentalMain).not.toContain('getAccountPasswordById(newDeal.account_id)')
    expect(newRentalSide).toContain('getAccountPasswordById(newDeal.account_id)')
    expect(newRentalSide).toContain('getDealReserveLabel(newDeal.account_id, newDeal.reserve_key)')
    expect(source.indexOf('<span class="label">Логин</span>'))
      .toBeLessThan(source.indexOf('<span class="label">Пароль</span>'))
  })

  it('hides refund field in pending and draft statuses and keeps it only for other flows', () => {
    const source = readTemplateSource()

    expect(source).toContain("editDeal.deal_type_code === 'rental' && !isEditDealPendingFlow")
    expect(source).toContain("editDeal.deal_type_code === 'sale' && !isEditDealPendingFlow")
    expect(source).toContain("const isEditDealPendingFlow = computed(() => {")
    expect(source).toContain("return status === 'pending' || status === 'draft'")
    expect(source).toContain("status === 'completed' && Boolean(allowCompletedDealEdit?.value)")
  })
})
