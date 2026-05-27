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
    expect(source).toContain(':size="newDeal.subscription_term_id ? 1 : 3"')
    expect(source).toContain(':size="editDeal.subscription_term_id ? 1 : 3"')
    expect(source).toContain(':size="newDeal.product_id ? 1 : 3"')
    expect(source).toContain(':size="editDeal.product_id ? 1 : 3"')
  })

  it('uses slot-first flow controls for subscriptions in create and edit', () => {
    const source = readTemplateSource()

    expect(source).toContain("v-if=\"showNewDealProductSearch\"")
    expect(source).toContain("v-if=\"dealEditMode !== 'view' && showEditDealProductSearch\"")
    expect(source).toContain('isNewRentalSubscriptionMode && !newDeal.slot_type_code')
    expect(source).toContain('isEditRentalSubscriptionMode && !editDeal.slot_type_code')
    expect(source).toContain("getSlotTypeOptionsForDeal('new')")
    expect(source).toContain("getSlotTypeOptionsForDeal('edit')")
    expect(source).toContain('if (!editDeal.value?.slot_type_code) return []')
    expect(source).toContain('if (!newDeal.value?.slot_type_code) return []')
    expect(source).toContain('return typed')
    expect(source).not.toContain('hasFreeSubscriptionSlotByProductId')
    expect(source).toContain('availableSubscriptionItemsNewFiltered')
    expect(source).toContain('availableSubscriptionItemsEditFiltered')
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
    expect(source).toContain('!isEditRentalSubscriptionMode || showEditDealProductSearch || editDeal.subscription_term_id')
    expect(source).toContain('!isNewRentalSubscriptionMode || showNewDealProductSearch || newDeal.subscription_term_id')
    expect(source).toContain('isEditRentalSubscriptionMode && editDeal.product_id && editDeal.slot_type_code && !editDeal.subscription_term_id')
    expect(source).toContain('isNewRentalSubscriptionMode && newDeal.product_id && newDeal.slot_type_code && !newDeal.subscription_term_id')
    expect(source).toContain("v-if=\"isEditRentalSubscriptionMode && editDeal.product_id && !editDeal.subscription_term_id\"")
    expect(source).toContain("v-if=\"isNewRentalSubscriptionMode && newDeal.product_id && !newDeal.subscription_term_id\"")
  })

  it('renders quick create blocks as collapsible toggles', () => {
    const source = readTemplateSource()
    const newRentalMain = source.match(/<div class="deal-form__rental-main">[\s\S]*?<div class="deal-form__rental-side">/)?.[0] || ''
    const newRentalSide = source.match(/<div class="deal-form__rental-side">[\s\S]*?<\/div>\s*<\/div>\s*<div v-if="newDeal\.deal_type_code === 'sale'"/)?.[0] || ''

    expect(source).toContain("const editQuickProductOpen = ref(false)")
    expect(source).toContain("const editQuickAccountOpen = ref(false)")
    expect(source).toContain("const editQuickSubscriptionTermOpen = ref(false)")
    expect(source).toContain("const newQuickProductOpen = ref(false)")
    expect(source).toContain("const newQuickAccountOpen = ref(false)")
    expect(source).toContain("const newQuickSubscriptionTermOpen = ref(false)")
    expect(source).toContain("'+ Быстрое создание товара'")
    expect(source).toContain("'+ Быстрое создание аккаунта'")
    expect(source).toContain('placeholder="Пароль аккаунта"')
    expect(source).toContain('placeholder="Комментарий"')
    expect(source).toContain('subscription_product_id')
    expect(source).toContain('— подписка —')
    expect(source).toContain('showNewQuickAccountReminder')
    expect(source).toContain('showEditQuickAccountReminder')
    expect(source).toContain('deal-form__quick-reminder--top')
    expect(source).toContain('Напоминание: заполните быстрый аккаунт до конца')
    expect(source).toContain('Осталось заполнить:')
    expect(source).toContain("'+ Добавить срок подписки'")
    expect(source).toContain('v-if="editQuickProductOpen"')
    expect(source).toContain('v-if="editQuickAccountOpen"')
    expect(source).toContain('v-if="editQuickSubscriptionTermOpen"')
    expect(source).toContain('v-if="newQuickProductOpen"')
    expect(source).toContain('v-if="newQuickAccountOpen"')
    expect(source).toContain('v-if="newQuickSubscriptionTermOpen"')
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
    expect(source).toContain("getDealReserveLabel(editDeal.account_id, editDeal.reserve_key, editDeal.deal_id, { allowFallback: dealEditMode === 'edit', emptyLabel: '— не назначен' })")
    expect(source).toContain('v-if="newDeal.account_id"')
    expect(source).toContain('getAccountPasswordById(newDeal.account_id)')
    expect(source).toContain('getDealReserveLabel(newDeal.account_id, newDeal.reserve_key, null, { allowFallback: true })')
    expect(source).toContain("getDealAccountLoginLabel('edit')")
    expect(source).toContain("getDealAccountLoginLabel('new')")
    expect(source).toContain('function getDealAccountLoginLabel(target)')
    expect(source).toContain("return hasHumanDealAccountLabel(accountId, label) ? label : '—'")
    expect(source).not.toContain('getAccountLabelById(editDeal.account_id)')
    expect(source).not.toContain('getAccountLabelById(newDeal.account_id)')
    expect(source).toContain('deal-form__account-details-head')
    expect(source).toContain('Данные аккаунта')
    expect(source).toContain('const value = String(getAccountSecret.value?.(accountId) || \'\').trim()')
    expect(source).toContain('function getUsedReserveKeysByAccount(accountId, currentDealId = null)')
    expect(source).toContain('const entries = Array.isArray(getReserveSecretEntries.value?.(accountId))')
    expect(source).not.toContain('deal-form__account-details">\n                          <div class="deal-form__double">')
    expect(source).toContain('deal-form__account-details-head">Данные аккаунта</div>')
    expect(newRentalMain).not.toContain('getAccountPasswordById(newDeal.account_id)')
    expect(newRentalSide).toContain('getAccountPasswordById(newDeal.account_id)')
    expect(newRentalSide).toContain('getDealReserveLabel(newDeal.account_id, newDeal.reserve_key, null, { allowFallback: true })')
    expect(source.indexOf('<span class="label">Логин</span>'))
      .toBeLessThan(source.indexOf('<span class="label">Пароль</span>'))
  })

  it('renders copy actions for sharing login, password and reserve', () => {
    const source = readTemplateSource()

    expect(source).toContain("copySharingField('edit', 'login')")
    expect(source).toContain("copySharingField('edit', 'password')")
    expect(source).toContain("copySharingField('edit', 'reserve')")
    expect(source).toContain("copySharingField('new', 'login')")
    expect(source).toContain("copySharingField('new', 'password')")
    expect(source).toContain("copySharingField('new', 'reserve')")
    expect(source).toContain('function getSharingFieldCopyLabel(target, field)')
    expect(source).toContain('function getSharingFieldCopyValue(target, field)')
    expect(source).toContain('function copySharingField(target, field)')
    expect(source).toContain('const copiedSharingFieldKey = ref(\'\')')
  })

  it('supports forced duplicate mode in create and edit sharing forms', () => {
    const source = readTemplateSource()

    expect(source).toContain("const forceNewDuplicateMode = ref(false)")
    expect(source).toContain("const forceEditDuplicateMode = ref(false)")
    expect(source).toContain("const canForceNewDuplicate = computed(() => {")
    expect(source).toContain("const canForceEditDuplicate = computed(() => {")
    expect(source).toContain("const shouldShowNewDuplicateList = computed(() => {")
    expect(source).toContain("const shouldShowEditDuplicateList = computed(() => {")
    expect(source).toContain("{{ forceNewDuplicateMode ? 'Скрыть дубли' : 'Сделать дубль' }}")
    expect(source).toContain("{{ forceEditDuplicateMode ? 'Скрыть дубли' : 'Сделать дубль' }}")
    expect(source).toContain('v-if="shouldShowNewDuplicateList"')
    expect(source).toContain('v-if="shouldShowEditDuplicateList"')
  })

  it('shows warning when selected sharing account has no free reserve', () => {
    const source = readTemplateSource()

    expect(source).toContain("showDealWarning.value('У выбранного аккаунта нет доступных резервов')")
    expect(source).toContain('const reserveKey = pickFirstFreeReserveKey(accountId)')
    expect(source).toContain('newDeal.value.reserve_key = reserveKey')
    expect(source).toContain('if (!normalizedKey && !allowFallback) return emptyLabel')
  })

  it('hides refund field in pending and draft statuses and keeps it only for other flows', () => {
    const source = readTemplateSource()

    expect(source).toContain("editDeal.deal_type_code === 'rental' && !isEditDealPendingFlow")
    expect(source).toContain("editDeal.deal_type_code === 'sale' && !isEditDealPendingFlow")
    expect(source).toContain("const isEditDealPendingFlow = computed(() => {")
    expect(source).toContain("return status === 'pending' || status === 'draft'")
    expect(source).toContain("return Boolean(allowCompletedDealEdit?.value)")
  })

  it('renders messenger and new sale field order', () => {
    const source = readTemplateSource()

    expect(source).toContain('<span class="label">Мессенджер</span>')
    expect(source).toContain('getMessengerLabelById(editDeal.messenger_id)')
    expect(source).toContain('v-model.number="newDeal.messenger_id"')
    expect(source).toContain('v-model.number="editDeal.messenger_id"')
    expect(source).toContain('<span class="label">Номер заказа</span>')
    expect(source).toContain('<span class="label">Ответственный</span>')
    expect(source).toContain('Ссылка на товар</span>')
    expect(source).toContain("v-if=\"newDeal.deal_type_code === 'sale'\" class=\"deal-form__sale-layout\"")
    expect(source).not.toContain('Данные об аккаунте')
    expect(source).toContain('deal-form__sale-group deal-form__sale-group--source')
    expect(source).toContain('deal-form__sale-group deal-form__sale-group--price')
    expect(source).toContain('<span class="label">Метод оплаты</span>')
    expect(source).toContain('<span class="label">Скидка</span>')
    expect(source).toContain('deal-form__input--locked')
    expect(source).toContain('input--with-copy')
    expect(source).toContain("v-for=\"(linkValue, linkIndex) in editSaleProductLinks\"")
    expect(source).toContain("v-for=\"(linkValue, linkIndex) in newSaleProductLinks\"")
    expect(source).toContain("copySaleProductLink('edit', linkIndex)")
    expect(source).toContain("copySaleProductLink('new', linkIndex)")
    expect(source).toContain("+ Добавить ссылку")
    expect(source).toContain('function setSaleProductLinkValue(target, index, value)')
    expect(source).toContain('function addSaleProductLink(target)')
    expect(source).toContain('function removeSaleProductLink(target, index)')
    expect(source).toContain('function copySaleProductLink(target, index = 0)')
    expect(source).toContain('function getSaleLinkCopyLabel(target, index = 0)')
  })

  it('renders sharing layout with locked payment and discount fields', () => {
    const source = readTemplateSource()
    const newRentalMain = source.match(/<div class="deal-form__rental-main">[\s\S]*?<div class="deal-form__rental-side">/)?.[0] || ''
    const editRentalMain = source.match(/<div class="deal-form__rental-main">[\s\S]*?<div class="deal-form__rental-side">/)?.[0] || ''

    expect(source).toContain('<span class="label">Номер заказа</span>')
    expect(source).toContain('<span class="label">Сумма продажи</span>')
    expect(source).toContain('<span class="label">Метод оплаты</span>')
    expect(source).toContain('<span class="label">Скидка</span>')
    expect(source).toContain('deal-form__input--locked')
    expect(source).toContain('Аккаунт')
    expect(source).toContain('+ Комментарий')
    expect(newRentalMain).toContain('<span class="label">Источник</span>')
    expect(newRentalMain).toContain('<span class="label">Мессенджер</span>')
    expect(newRentalMain).toContain('<span class="label">Покупатель</span>')
    expect(newRentalMain).toContain('<span class="label">Ответственный</span>')
    expect(editRentalMain).toContain('<span class="label">Номер заказа</span>')
    expect(editRentalMain).toContain('<span class="label">Сумма продажи</span>')
  })
})
